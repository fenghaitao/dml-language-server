//! DML MCP Server main entry point
//! 
//! This binary provides an MCP server for DML code generation using the
//! existing DML Language Server analysis capabilities.

use anyhow::Result;
use dls::mcp::DMLMCPServer;
use env_logger;
use log::info;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();
    
    info!("Starting DML MCP Server v{}", env!("CARGO_PKG_VERSION"));
    
    // Create and run the MCP server
    let server = DMLMCPServer::new().await?;
    server.run().await?;
    
    Ok(())
}