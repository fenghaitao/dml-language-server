//! MCP Server implementation for DML code generation

use anyhow::{anyhow, Result};
use log::{debug, error, info, warn};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

use crate::mcp::{ServerCapabilities, ServerInfo, MCP_VERSION};
use crate::mcp::tools::ToolRegistry;

/// MCP JSON-RPC message
#[derive(Debug, Serialize, Deserialize)]
pub struct JsonRpcMessage {
    pub jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub method: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

/// DML MCP Server
pub struct DMLMCPServer {
    tool_registry: ToolRegistry,
    server_info: ServerInfo,
    capabilities: ServerCapabilities,
}

impl DMLMCPServer {
    /// Create a new MCP server instance
    pub async fn new() -> Result<Self> {
        info!("Initializing DML MCP Server");
        
        let tool_registry = ToolRegistry::new().await?;
        
        Ok(Self {
            tool_registry,
            server_info: ServerInfo::default(),
            capabilities: ServerCapabilities::default(),
        })
    }
    
    /// Run the MCP server
    pub async fn run(&self) -> Result<()> {
        info!("Starting MCP server on stdio");
        
        let stdin = tokio::io::stdin();
        let mut stdout = tokio::io::stdout();
        let mut reader = BufReader::new(stdin);
        let mut line = String::new();
        
        loop {
            line.clear();
            match reader.read_line(&mut line).await {
                Ok(0) => {
                    debug!("EOF reached, shutting down");
                    break;
                }
                Ok(_) => {
                    if let Err(e) = self.handle_message(&line, &mut stdout).await {
                        error!("Error handling message: {}", e);
                    }
                }
                Err(e) => {
                    error!("Error reading from stdin: {}", e);
                    break;
                }
            }
        }
        
        Ok(())
    }
    
    /// Handle incoming MCP message
    async fn handle_message(
        &self,
        line: &str,
        stdout: &mut tokio::io::Stdout,
    ) -> Result<()> {
        let line = line.trim();
        if line.is_empty() {
            return Ok(());
        }
        
        debug!("Received message: {}", line);
        
        let message: JsonRpcMessage = serde_json::from_str(line)
            .map_err(|e| anyhow!("Failed to parse JSON-RPC message: {}", e))?;
        
        let response = match message.method.as_deref() {
            Some("initialize") => self.handle_initialize(&message).await,
            Some("tools/list") => self.handle_tools_list(&message).await,
            Some("tools/call") => self.handle_tools_call(&message).await,
            Some(method) => {
                warn!("Unknown method: {}", method);
                self.create_error_response(
                    message.id,
                    -32601,
                    "Method not found",
                    None,
                )
            }
            None => {
                // This might be a response to a request we sent
                debug!("Received response/notification: {:?}", message);
                return Ok(());
            }
        };
        
        let response_json = serde_json::to_string(&response)?;
        debug!("Sending response: {}", response_json);
        
        stdout.write_all(response_json.as_bytes()).await?;
        stdout.write_all(b"\n").await?;
        stdout.flush().await?;
        
        Ok(())
    }
    
    /// Handle initialize request
    async fn handle_initialize(&self, message: &JsonRpcMessage) -> JsonRpcMessage {
        info!("Handling initialize request");
        
        let result = json!({
            "protocolVersion": MCP_VERSION,
            "capabilities": self.capabilities,
            "serverInfo": self.server_info
        });
        
        JsonRpcMessage {
            jsonrpc: "2.0".to_string(),
            id: message.id.clone(),
            method: None,
            params: None,
            result: Some(result),
            error: None,
        }
    }
    
    /// Handle tools/list request
    async fn handle_tools_list(&self, message: &JsonRpcMessage) -> JsonRpcMessage {
        debug!("Handling tools/list request");
        
        let tools = self.tool_registry.list_tools();
        let result = json!({
            "tools": tools
        });
        
        JsonRpcMessage {
            jsonrpc: "2.0".to_string(),
            id: message.id.clone(),
            method: None,
            params: None,
            result: Some(result),
            error: None,
        }
    }
    
    /// Handle tools/call request
    async fn handle_tools_call(&self, message: &JsonRpcMessage) -> JsonRpcMessage {
        debug!("Handling tools/call request");
        
        match &message.params {
            Some(params) => {
                match self.tool_registry.call_tool(params).await {
                    Ok(result) => JsonRpcMessage {
                        jsonrpc: "2.0".to_string(),
                        id: message.id.clone(),
                        method: None,
                        params: None,
                        result: Some(result),
                        error: None,
                    },
                    Err(e) => {
                        error!("Tool call failed: {}", e);
                        self.create_error_response(
                            message.id.clone(),
                            -32603,
                            "Internal error",
                            Some(json!({"details": e.to_string()})),
                        )
                    }
                }
            }
            None => self.create_error_response(
                message.id.clone(),
                -32602,
                "Invalid params",
                Some(json!({"details": "Missing params for tools/call"})),
            ),
        }
    }
    
    /// Create error response
    fn create_error_response(
        &self,
        id: Option<Value>,
        code: i32,
        message: &str,
        data: Option<Value>,
    ) -> JsonRpcMessage {
        JsonRpcMessage {
            jsonrpc: "2.0".to_string(),
            id,
            method: None,
            params: None,
            result: None,
            error: Some(JsonRpcError {
                code,
                message: message.to_string(),
                data,
            }),
        }
    }
}