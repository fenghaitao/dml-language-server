//! MCP (Model Context Protocol) server for DML code generation
//! 
//! This module provides an MCP server that leverages the existing DML analysis
//! capabilities to offer intelligent code generation tools.

pub mod server;
pub mod tools;
pub mod generation;
pub mod templates;

pub use server::DMLMCPServer;
pub use tools::*;
pub use generation::*;
pub use templates::*;
use serde::{Deserialize, Serialize};

/// MCP protocol version supported
pub const MCP_VERSION: &str = "2024-11-05";

/// Server information
#[derive(Debug, Serialize, Deserialize)]
pub struct ServerInfo {
    pub name: String,
    pub version: String,
}

impl Default for ServerInfo {
    fn default() -> Self {
        Self {
            name: "dml-mcp-server".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
        }
    }
}

/// MCP server capabilities
#[derive(Debug, Serialize, Deserialize)]
pub struct ServerCapabilities {
    pub tools: bool,
    pub resources: bool,
    pub prompts: bool,
    pub logging: bool,
}

impl Default for ServerCapabilities {
    fn default() -> Self {
        Self {
            tools: true,
            resources: false,
            prompts: false,
            logging: true,
        }
    }
}