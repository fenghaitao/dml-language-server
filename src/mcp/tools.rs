//! DML code generation tools for MCP

use anyhow::{anyhow, Result};
use async_trait::async_trait;
use log::{debug, info};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;

use crate::config::Config;

/// Tool execution result
#[derive(Debug, Serialize, Deserialize)]
pub struct ToolResult {
    pub content: Vec<ToolContent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub is_error: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ToolContent {
    #[serde(rename = "type")]
    pub content_type: String,
    pub text: String,
}

/// Tool definition for MCP
#[derive(Debug, Serialize, Deserialize)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    #[serde(rename = "inputSchema")]
    pub input_schema: Value,
}

/// Trait for DML tools
#[async_trait]
pub trait DMLTool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    fn input_schema(&self) -> Value;
    async fn execute(&self, input: Value) -> Result<ToolResult>;
}

/// Tool registry managing all available tools
pub struct ToolRegistry {
    tools: HashMap<String, Box<dyn DMLTool>>,
    config: Config,
}

impl ToolRegistry {
    pub async fn new() -> Result<Self> {
        let config = Config::default();
        let mut registry = Self {
            tools: HashMap::new(),
            config,
        };
        
        // Register built-in tools
        registry.register_builtin_tools().await?;
        
        info!("Registered {} DML tools", registry.tools.len());
        Ok(registry)
    }
    
    async fn register_builtin_tools(&mut self) -> Result<()> {
        // Device generation tools
        self.register_tool(Box::new(GenerateDeviceTool::new())).await?;
        self.register_tool(Box::new(GenerateRegisterTool::new())).await?;
        self.register_tool(Box::new(GenerateMethodTool::new())).await?;
        
        // Analysis tools
        self.register_tool(Box::new(AnalyzeProjectTool::new())).await?;
        self.register_tool(Box::new(ValidateCodeTool::new())).await?;
        
        // Template tools
        self.register_tool(Box::new(GenerateTemplateTool::new())).await?;
        self.register_tool(Box::new(ApplyPatternTool::new())).await?;
        
        Ok(())
    }
    
    async fn register_tool(&mut self, tool: Box<dyn DMLTool>) -> Result<()> {
        let name = tool.name().to_string();
        debug!("Registering tool: {}", name);
        self.tools.insert(name, tool);
        Ok(())
    }
    
    pub fn list_tools(&self) -> Vec<ToolDefinition> {
        self.tools
            .values()
            .map(|tool| ToolDefinition {
                name: tool.name().to_string(),
                description: tool.description().to_string(),
                input_schema: tool.input_schema(),
            })
            .collect()
    }
    
    pub async fn call_tool(&self, params: &Value) -> Result<Value> {
        let tool_name = params
            .get("name")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing tool name"))?;
        
        let arguments = params
            .get("arguments")
            .ok_or_else(|| anyhow!("Missing tool arguments"))?;
        
        let tool = self
            .tools
            .get(tool_name)
            .ok_or_else(|| anyhow!("Unknown tool: {}", tool_name))?;
        
        debug!("Executing tool: {} with args: {}", tool_name, arguments);
        
        let result = tool.execute(arguments.clone()).await?;
        Ok(serde_json::to_value(result)?)
    }
}

// ========== Built-in Tools ==========

/// Generate a complete DML device
pub struct GenerateDeviceTool;

impl GenerateDeviceTool {
    pub fn new() -> Self {
        Self
    }
}

#[async_trait]
impl DMLTool for GenerateDeviceTool {
    fn name(&self) -> &str {
        "generate_device"
    }
    
    fn description(&self) -> &str {
        "Generate a complete DML device model with specified configuration"
    }
    
    fn input_schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "device_name": {
                    "type": "string",
                    "description": "Name of the device to generate"
                },
                "device_type": {
                    "type": "string",
                    "enum": ["cpu", "memory", "peripheral", "custom"],
                    "description": "Type of device to generate"
                },
                "registers": {
                    "type": "array",
                    "description": "List of registers to include",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "size": {"type": "integer"},
                            "offset": {"type": "string"}
                        }
                    }
                },
                "interfaces": {
                    "type": "array",
                    "description": "Interfaces to implement",
                    "items": {"type": "string"}
                },
                "template_base": {
                    "type": "string",
                    "description": "Base template to inherit from"
                }
            },
            "required": ["device_name", "device_type"]
        })
    }
    
    async fn execute(&self, input: Value) -> Result<ToolResult> {
        let device_name = input["device_name"]
            .as_str()
            .ok_or_else(|| anyhow!("Missing device_name"))?;
        
        let device_type = input["device_type"]
            .as_str()
            .ok_or_else(|| anyhow!("Missing device_type"))?;
        
        // Generate device code based on parameters
        let generated_code = generate_device_code(device_name, device_type, &input)?;
        
        Ok(ToolResult {
            content: vec![ToolContent {
                content_type: "text".to_string(),
                text: generated_code,
            }],
            is_error: None,
        })
    }
}

/// Generate DML register with fields
pub struct GenerateRegisterTool;

impl GenerateRegisterTool {
    pub fn new() -> Self {
        Self
    }
}

#[async_trait]
impl DMLTool for GenerateRegisterTool {
    fn name(&self) -> &str {
        "generate_register"
    }
    
    fn description(&self) -> &str {
        "Generate a DML register with specified fields and properties"
    }
    
    fn input_schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the register"
                },
                "size": {
                    "type": "integer",
                    "description": "Size of the register in bytes"
                },
                "offset": {
                    "type": "string",
                    "description": "Offset address (e.g., '0x100')"
                },
                "fields": {
                    "type": "array",
                    "description": "Register fields",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "bits": {"type": "string"},
                            "access": {"type": "string"}
                        }
                    }
                },
                "documentation": {
                    "type": "string",
                    "description": "Documentation for the register"
                }
            },
            "required": ["name", "size"]
        })
    }
    
    async fn execute(&self, input: Value) -> Result<ToolResult> {
        let register_name = input["name"]
            .as_str()
            .ok_or_else(|| anyhow!("Missing register name"))?;
        
        let size = input["size"]
            .as_u64()
            .ok_or_else(|| anyhow!("Missing or invalid register size"))?;
        
        let generated_code = generate_register_code(register_name, size, &input)?;
        
        Ok(ToolResult {
            content: vec![ToolContent {
                content_type: "text".to_string(),
                text: generated_code,
            }],
            is_error: None,
        })
    }
}

// Placeholder implementations for other tools
macro_rules! impl_placeholder_tool {
    ($name:ident, $tool_name:expr, $description:expr) => {
        pub struct $name;
        
        impl $name {
            pub fn new() -> Self {
                Self
            }
        }
        
        #[async_trait]
        impl DMLTool for $name {
            fn name(&self) -> &str {
                $tool_name
            }
            
            fn description(&self) -> &str {
                $description
            }
            
            fn input_schema(&self) -> Value {
                json!({"type": "object", "properties": {}})
            }
            
            async fn execute(&self, _input: Value) -> Result<ToolResult> {
                Ok(ToolResult {
                    content: vec![ToolContent {
                        content_type: "text".to_string(),
                        text: format!("Tool '{}' is not yet implemented", self.name()),
                    }],
                    is_error: Some(false),
                })
            }
        }
    };
}

impl_placeholder_tool!(GenerateMethodTool, "generate_method", "Generate DML method implementation");
impl_placeholder_tool!(AnalyzeProjectTool, "analyze_project", "Analyze existing DML project structure");
impl_placeholder_tool!(ValidateCodeTool, "validate_code", "Validate DML code syntax and semantics");
impl_placeholder_tool!(GenerateTemplateTool, "generate_template", "Generate reusable DML templates");
impl_placeholder_tool!(ApplyPatternTool, "apply_pattern", "Apply common DML design patterns");

// ========== Code Generation Functions ==========

fn generate_device_code(name: &str, device_type: &str, params: &Value) -> Result<String> {
    let template_base = params["template_base"]
        .as_str()
        .unwrap_or("base_device");
    
    let mut code = format!(
        r#"dml 1.4;

device {} : {} {{
    /// Generated {} device
    
"#,
        name, template_base, device_type
    );
    
    // Add registers if specified
    if let Some(registers) = params["registers"].as_array() {
        code.push_str("    bank registers {\n");
        for register in registers {
            if let (Some(reg_name), Some(reg_size)) = 
                (register["name"].as_str(), register["size"].as_u64()) {
                let offset = register["offset"].as_str().unwrap_or("undefined");
                code.push_str(&format!(
                    "        register {} size {} @ {};\n",
                    reg_name, reg_size, offset
                ));
            }
        }
        code.push_str("    }\n");
    }
    
    // Add interfaces if specified
    if let Some(interfaces) = params["interfaces"].as_array() {
        for interface in interfaces {
            if let Some(iface) = interface.as_str() {
                code.push_str(&format!("    implement {};\n", iface));
            }
        }
    }
    
    code.push_str("}\n");
    
    Ok(code)
}

fn generate_register_code(name: &str, size: u64, params: &Value) -> Result<String> {
    let mut code = format!("register {} size {} {{\n", name, size);
    
    // Add documentation if provided
    if let Some(doc) = params["documentation"].as_str() {
        code.push_str(&format!("    /// {}\n", doc));
    }
    
    // Add fields if specified
    if let Some(fields) = params["fields"].as_array() {
        for field in fields {
            if let Some(field_name) = field["name"].as_str() {
                let bits = field["bits"].as_str().unwrap_or("0");
                let access = field["access"].as_str().unwrap_or("rw");
                
                code.push_str(&format!(
                    "    field {} @ [{}] access {};\n",
                    field_name, bits, access
                ));
            }
        }
    }
    
    code.push_str("}\n");
    
    Ok(code)
}