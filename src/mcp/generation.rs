//! Code generation engine for DML

use anyhow::Result;
use log::{debug, info};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Code generation context
#[derive(Debug, Clone)]
pub struct GenerationContext {
    pub device_name: String,
    pub namespace: String,
    pub imports: Vec<String>,
    pub templates: Vec<String>,
    pub config: GenerationConfig,
}

/// Generation configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationConfig {
    pub indent_style: IndentStyle,
    pub line_ending: LineEnding,
    pub max_line_length: usize,
    pub generate_docs: bool,
    pub validate_output: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IndentStyle {
    Spaces(usize),
    Tabs,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LineEnding {
    Unix,
    Windows,
}

impl Default for GenerationConfig {
    fn default() -> Self {
        Self {
            indent_style: IndentStyle::Spaces(4),
            line_ending: LineEnding::Unix,
            max_line_length: 100,
            generate_docs: true,
            validate_output: true,
        }
    }
}

/// DML code generator
pub struct DMLGenerator {
    pub context: GenerationContext,
    templates: TemplateRegistry,
}

impl DMLGenerator {
    pub fn new(context: GenerationContext) -> Self {
        Self {
            context,
            templates: TemplateRegistry::new(),
        }
    }
    
    /// Generate a complete device
    pub async fn generate_device(
        &self,
        device_spec: &DeviceSpec,
    ) -> Result<GeneratedCode> {
        info!("Generating device: {}", device_spec.name);
        
        let mut code = String::new();
        
        // Generate header
        code.push_str(&self.generate_header()?);
        
        // Generate device declaration
        code.push_str(&self.generate_device_declaration(device_spec)?);
        
        // Generate banks
        for bank in &device_spec.banks {
            code.push_str(&self.generate_bank(bank).await?);
        }
        
        // Generate interfaces
        for interface in &device_spec.interfaces {
            code.push_str(&self.generate_interface(interface)?);
        }
        
        // Generate methods
        for method in &device_spec.methods {
            code.push_str(&self.generate_method(method)?);
        }
        
        // Close device
        code.push_str("}\n");
        
        let generated = GeneratedCode {
            content: code,
            file_path: format!("{}.dml", device_spec.name),
            dependencies: device_spec.dependencies.clone(),
        };
        
        // Validate if requested
        if self.context.config.validate_output {
            self.validate_generated_code(&generated).await?;
        }
        
        Ok(generated)
    }
    
    /// Generate a register
    pub async fn generate_register(
        &self,
        register_spec: &RegisterSpec,
    ) -> Result<String> {
        debug!("Generating register: {}", register_spec.name);
        
        let mut code = String::new();
        
        // Add documentation
        if self.context.config.generate_docs {
            if let Some(doc) = &register_spec.documentation {
                code.push_str(&format!("    /// {}\n", doc));
            }
        }
        
        // Register declaration
        code.push_str(&format!(
            "    register {} size {}",
            register_spec.name,
            register_spec.size
        ));
        
        // Add offset if specified
        if let Some(offset) = &register_spec.offset {
            code.push_str(&format!(" @ {}", offset));
        }
        
        code.push_str(" {\n");
        
        // Generate fields
        for field in &register_spec.fields {
            code.push_str(&self.generate_field(field)?);
        }
        
        // Add methods if any
        for method in &register_spec.methods {
            code.push_str(&self.generate_method(method)?);
        }
        
        code.push_str("    }\n");
        
        Ok(code)
    }
    
    /// Generate a method
    pub fn generate_method(&self, method_spec: &MethodSpec) -> Result<String> {
        debug!("Generating method: {}", method_spec.name);
        
        let mut code = String::new();
        let indent = self.get_indent();
        
        // Add documentation
        if self.context.config.generate_docs {
            if let Some(doc) = &method_spec.documentation {
                code.push_str(&format!("{}/// {}\n", indent, doc));
            }
        }
        
        // Method signature
        code.push_str(&format!("{}method {}", indent, method_spec.name));
        
        // Parameters
        if !method_spec.parameters.is_empty() {
            code.push('(');
            for (i, param) in method_spec.parameters.iter().enumerate() {
                if i > 0 {
                    code.push_str(", ");
                }
                code.push_str(&format!("{}: {}", param.name, param.param_type));
            }
            code.push(')');
        }
        
        // Return type
        if let Some(return_type) = &method_spec.return_type {
            code.push_str(&format!(" -> {}", return_type));
        }
        
        code.push_str(" {\n");
        
        // Method body
        if let Some(body) = &method_spec.body {
            code.push_str(&format!("{}    {}\n", indent, body));
        } else {
            code.push_str(&format!("{}    // TODO: Implement method\n", indent));
        }
        
        code.push_str(&format!("{}}}\n", indent));
        
        Ok(code)
    }
    
    fn generate_header(&self) -> Result<String> {
        let mut header = String::new();
        
        header.push_str("dml 1.4;\n\n");
        
        // Add imports
        for import in &self.context.imports {
            header.push_str(&format!("import \"{}\";\n", import));
        }
        
        if !self.context.imports.is_empty() {
            header.push('\n');
        }
        
        Ok(header)
    }
    
    fn generate_device_declaration(&self, device_spec: &DeviceSpec) -> Result<String> {
        let mut code = String::new();
        
        // Device documentation
        if self.context.config.generate_docs {
            if let Some(doc) = &device_spec.documentation {
                code.push_str(&format!("/// {}\n", doc));
            }
        }
        
        // Device declaration
        code.push_str(&format!("device {}", device_spec.name));
        
        // Inheritance
        if let Some(base) = &device_spec.base_template {
            code.push_str(&format!(" : {}", base));
        }
        
        code.push_str(" {\n");
        
        Ok(code)
    }
    
    async fn generate_bank(&self, bank_spec: &BankSpec) -> Result<String> {
        let mut code = String::new();
        let indent = self.get_indent();
        
        if self.context.config.generate_docs {
            if let Some(doc) = &bank_spec.documentation {
                code.push_str(&format!("{}/// {}\n", indent, doc));
            }
        }
        
        code.push_str(&format!("{}bank {} {{\n", indent, bank_spec.name));
        
        // Generate registers
        for register in &bank_spec.registers {
            let register_code = self.generate_register(register).await?;
            code.push_str(&register_code);
        }
        
        code.push_str(&format!("{}}}\n", indent));
        
        Ok(code)
    }
    
    fn generate_interface(&self, interface_spec: &InterfaceSpec) -> Result<String> {
        let indent = self.get_indent();
        Ok(format!("{}implement {};\n", indent, interface_spec.name))
    }
    
    fn generate_field(&self, field_spec: &FieldSpec) -> Result<String> {
        let mut code = String::new();
        let indent = "        "; // Double indent for field
        
        if self.context.config.generate_docs {
            if let Some(doc) = &field_spec.documentation {
                code.push_str(&format!("{}/// {}\n", indent, doc));
            }
        }
        
        code.push_str(&format!(
            "{}field {} @ [{}]",
            indent, field_spec.name, field_spec.bits
        ));
        
        if let Some(access) = &field_spec.access {
            code.push_str(&format!(" access {}", access));
        }
        
        code.push_str(";\n");
        
        Ok(code)
    }
    
    pub fn get_indent(&self) -> String {
        match self.context.config.indent_style {
            IndentStyle::Spaces(n) => " ".repeat(n),
            IndentStyle::Tabs => "\t".to_string(),
        }
    }
    
    async fn validate_generated_code(&self, _generated: &GeneratedCode) -> Result<()> {
        debug!("Validating generated code");
        // TODO: Integrate with existing DML parser for validation
        Ok(())
    }
}

/// Template registry for code generation
pub struct TemplateRegistry {
    templates: HashMap<String, CodeTemplate>,
}

impl TemplateRegistry {
    pub fn new() -> Self {
        let mut registry = Self {
            templates: HashMap::new(),
        };
        
        registry.load_builtin_templates();
        registry
    }
    
    fn load_builtin_templates(&mut self) {
        // TODO: Load built-in DML templates
    }
}

/// Code template
#[derive(Debug, Clone)]
pub struct CodeTemplate {
    pub name: String,
    pub content: String,
    pub parameters: Vec<TemplateParameter>,
}

#[derive(Debug, Clone)]
pub struct TemplateParameter {
    pub name: String,
    pub param_type: String,
    pub default_value: Option<String>,
}

/// Generated code result
#[derive(Debug)]
pub struct GeneratedCode {
    pub content: String,
    pub file_path: String,
    pub dependencies: Vec<String>,
}

// ========== Specification Types ==========

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceSpec {
    pub name: String,
    pub base_template: Option<String>,
    pub documentation: Option<String>,
    pub banks: Vec<BankSpec>,
    pub interfaces: Vec<InterfaceSpec>,
    pub methods: Vec<MethodSpec>,
    pub dependencies: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BankSpec {
    pub name: String,
    pub documentation: Option<String>,
    pub registers: Vec<RegisterSpec>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterSpec {
    pub name: String,
    pub size: u64,
    pub offset: Option<String>,
    pub documentation: Option<String>,
    pub fields: Vec<FieldSpec>,
    pub methods: Vec<MethodSpec>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldSpec {
    pub name: String,
    pub bits: String,
    pub access: Option<String>,
    pub documentation: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InterfaceSpec {
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MethodSpec {
    pub name: String,
    pub parameters: Vec<ParameterSpec>,
    pub return_type: Option<String>,
    pub body: Option<String>,
    pub documentation: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParameterSpec {
    pub name: String,
    pub param_type: String,
}