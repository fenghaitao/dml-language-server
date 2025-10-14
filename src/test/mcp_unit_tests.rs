//! Unit tests for DML MCP Server components

#[cfg(test)]
mod mcp_tests {
    use crate::mcp::{ServerInfo, ServerCapabilities, MCP_VERSION};
    use crate::mcp::generation::{
        GenerationContext, GenerationConfig, DMLGenerator, DeviceSpec, 
        RegisterSpec, FieldSpec, MethodSpec, ParameterSpec,
        IndentStyle, LineEnding
    };
    use crate::mcp::templates::DMLTemplates;
    use serde_json::json;

    #[test]
    fn test_server_info_default() {
        let info = ServerInfo::default();
        assert_eq!(info.name, "dml-mcp-server");
        assert_eq!(info.version, env!("CARGO_PKG_VERSION"));
    }

    #[test]
    fn test_server_capabilities_default() {
        let caps = ServerCapabilities::default();
        assert!(caps.tools);
        assert!(!caps.resources);
        assert!(!caps.prompts);
        assert!(caps.logging);
    }

    #[test]
    fn test_mcp_version() {
        assert_eq!(MCP_VERSION, "2024-11-05");
    }

    #[test]
    fn test_generation_config_default() {
        let config = GenerationConfig::default();
        
        match config.indent_style {
            IndentStyle::Spaces(n) => assert_eq!(n, 4),
            IndentStyle::Tabs => panic!("Expected spaces, got tabs"),
        }
        
        match config.line_ending {
            LineEnding::Unix => {},
            LineEnding::Windows => panic!("Expected Unix line endings"),
        }
        
        assert_eq!(config.max_line_length, 100);
        assert!(config.generate_docs);
        assert!(config.validate_output);
    }

    #[test]
    fn test_generation_context_creation() {
        let context = GenerationContext {
            device_name: "test_device".to_string(),
            namespace: "test".to_string(),
            imports: vec!["common.dml".to_string()],
            templates: vec!["base_device".to_string()],
            config: GenerationConfig::default(),
        };
        
        assert_eq!(context.device_name, "test_device");
        assert_eq!(context.namespace, "test");
        assert_eq!(context.imports.len(), 1);
        assert_eq!(context.templates.len(), 1);
    }

    #[test]
    fn test_device_spec_creation() {
        let device = DeviceSpec {
            name: "test_device".to_string(),
            base_template: Some("base_device".to_string()),
            documentation: Some("Test device".to_string()),
            banks: vec![],
            interfaces: vec![],
            methods: vec![],
            dependencies: vec![],
        };
        
        assert_eq!(device.name, "test_device");
        assert_eq!(device.base_template, Some("base_device".to_string()));
        assert_eq!(device.documentation, Some("Test device".to_string()));
    }

    #[test]
    fn test_register_spec_with_fields() {
        let field = FieldSpec {
            name: "enable".to_string(),
            bits: "0".to_string(),
            access: Some("rw".to_string()),
            documentation: Some("Enable bit".to_string()),
        };
        
        let register = RegisterSpec {
            name: "control".to_string(),
            size: 4,
            offset: Some("0x00".to_string()),
            documentation: Some("Control register".to_string()),
            fields: vec![field],
            methods: vec![],
        };
        
        assert_eq!(register.name, "control");
        assert_eq!(register.size, 4);
        assert_eq!(register.offset, Some("0x00".to_string()));
        assert_eq!(register.fields.len(), 1);
        assert_eq!(register.fields[0].name, "enable");
        assert_eq!(register.fields[0].bits, "0");
    }

    #[test]
    fn test_method_spec_creation() {
        let param = ParameterSpec {
            name: "value".to_string(),
            param_type: "uint32".to_string(),
        };
        
        let method = MethodSpec {
            name: "write".to_string(),
            parameters: vec![param],
            return_type: None,
            body: Some("val = value;".to_string()),
            documentation: Some("Write method".to_string()),
        };
        
        assert_eq!(method.name, "write");
        assert_eq!(method.parameters.len(), 1);
        assert_eq!(method.parameters[0].name, "value");
        assert_eq!(method.return_type, None);
        assert!(method.body.is_some());
    }

    #[test]
    fn test_dml_generator_creation() {
        let context = GenerationContext {
            device_name: "test".to_string(),
            namespace: "test".to_string(),
            imports: vec![],
            templates: vec![],
            config: GenerationConfig::default(),
        };
        
        let generator = DMLGenerator::new(context);
        assert_eq!(generator.context.device_name, "test");
    }

    #[tokio::test]
    async fn test_generate_register_basic() {
        let context = GenerationContext {
            device_name: "test".to_string(),
            namespace: "test".to_string(),
            imports: vec![],
            templates: vec![],
            config: GenerationConfig::default(),
        };
        
        let generator = DMLGenerator::new(context);
        
        let register_spec = RegisterSpec {
            name: "status".to_string(),
            size: 4,
            offset: Some("0x04".to_string()),
            documentation: Some("Status register".to_string()),
            fields: vec![],
            methods: vec![],
        };
        
        let result = generator.generate_register(&register_spec).await;
        assert!(result.is_ok());
        
        let code = result.unwrap();
        assert!(code.contains("register status"));
        assert!(code.contains("size 4"));
        assert!(code.contains("@ 0x04"));
        assert!(code.contains("/// Status register"));
    }

    #[tokio::test]
    async fn test_generate_register_with_fields() {
        let context = GenerationContext {
            device_name: "test".to_string(),
            namespace: "test".to_string(),
            imports: vec![],
            templates: vec![],
            config: GenerationConfig::default(),
        };
        
        let generator = DMLGenerator::new(context);
        
        let field = FieldSpec {
            name: "ready".to_string(),
            bits: "0".to_string(),
            access: Some("ro".to_string()),
            documentation: Some("Ready bit".to_string()),
        };
        
        let register_spec = RegisterSpec {
            name: "status".to_string(),
            size: 4,
            offset: Some("0x04".to_string()),
            documentation: Some("Status register".to_string()),
            fields: vec![field],
            methods: vec![],
        };
        
        let result = generator.generate_register(&register_spec).await;
        assert!(result.is_ok());
        
        let code = result.unwrap();
        assert!(code.contains("field ready"));
        assert!(code.contains("@ [0]"));
        assert!(code.contains("access ro"));
    }

    #[test]
    fn test_generate_method_code() {
        let context = GenerationContext {
            device_name: "test".to_string(),
            namespace: "test".to_string(),
            imports: vec![],
            templates: vec![],
            config: GenerationConfig::default(),
        };
        
        let generator = DMLGenerator::new(context);
        
        let param = ParameterSpec {
            name: "data".to_string(),
            param_type: "uint32".to_string(),
        };
        
        let method_spec = MethodSpec {
            name: "write".to_string(),
            parameters: vec![param],
            return_type: None,
            body: Some("register_value = data;".to_string()),
            documentation: Some("Write to register".to_string()),
        };
        
        let result = generator.generate_method(&method_spec);
        assert!(result.is_ok());
        
        let code = result.unwrap();
        assert!(code.contains("method write"));
        assert!(code.contains("data: uint32"));
        assert!(code.contains("register_value = data;"));
        assert!(code.contains("/// Write to register"));
    }

    #[test]
    fn test_basic_device_template() {
        let device = DMLTemplates::basic_device("test_cpu", "cpu");
        
        assert_eq!(device.name, "test_cpu");
        assert_eq!(device.base_template, Some("cpu_device".to_string()));
        assert!(device.documentation.is_some());
        assert!(device.documentation.unwrap().contains("cpu"));
    }

    #[test]
    fn test_memory_mapped_device_template() {
        let device = DMLTemplates::memory_mapped_device("test_peripheral", 0x1000, 0x100);
        
        assert_eq!(device.name, "test_peripheral");
        assert_eq!(device.banks.len(), 1);
        assert_eq!(device.banks[0].name, "registers");
        assert_eq!(device.banks[0].registers.len(), 2); // control and status
        assert_eq!(device.interfaces.len(), 1);
        assert_eq!(device.interfaces[0].name, "io_memory");
    }

    #[test]
    fn test_interrupt_controller_template() {
        let device = DMLTemplates::interrupt_controller("irq_ctrl", 32);
        
        assert_eq!(device.name, "irq_ctrl");
        assert_eq!(device.banks.len(), 1);
        assert_eq!(device.banks[0].registers.len(), 2); // irq_enable and irq_pending
        assert_eq!(device.interfaces.len(), 1);
        assert_eq!(device.interfaces[0].name, "signal");
        assert!(!device.methods.is_empty());
        
        // Check for signal_raise method
        let signal_method = device.methods.iter().find(|m| m.name == "signal_raise");
        assert!(signal_method.is_some());
    }

    #[test]
    fn test_cpu_device_template() {
        let device = DMLTemplates::cpu_device("riscv_core", "riscv");
        
        assert_eq!(device.name, "riscv_core");
        assert_eq!(device.base_template, Some("riscv_cpu".to_string()));
        assert_eq!(device.interfaces.len(), 3); // processor, cycle, execute
        assert!(!device.methods.is_empty());
        
        // Check for required methods
        let init_method = device.methods.iter().find(|m| m.name == "init");
        let reset_method = device.methods.iter().find(|m| m.name == "reset");
        assert!(init_method.is_some());
        assert!(reset_method.is_some());
    }

    #[test]
    fn test_memory_device_template() {
        let device = DMLTemplates::memory_device("system_ram", 64);
        
        assert_eq!(device.name, "system_ram");
        assert_eq!(device.banks.len(), 1);
        assert_eq!(device.banks[0].name, "memory");
        assert_eq!(device.interfaces.len(), 1);
        assert_eq!(device.interfaces[0].name, "io_memory");
        
        // Check for memory access methods
        let read_method = device.methods.iter().find(|m| m.name == "read");
        let write_method = device.methods.iter().find(|m| m.name == "write");
        assert!(read_method.is_some());
        assert!(write_method.is_some());
    }

    #[test]
    fn test_bus_interface_device_template() {
        let device = DMLTemplates::bus_interface_device("pci_bridge", 32);
        
        assert_eq!(device.name, "pci_bridge");
        assert_eq!(device.banks.len(), 1);
        assert_eq!(device.banks[0].name, "config");
        assert_eq!(device.interfaces.len(), 2); // io_memory and signal
        
        // Check bus config register
        let bus_config = device.banks[0].registers.iter().find(|r| r.name == "bus_config");
        assert!(bus_config.is_some());
        let config_reg = bus_config.unwrap();
        assert_eq!(config_reg.fields.len(), 2); // width and endian fields
    }

    #[test]
    fn test_pattern_templates_exist() {
        let patterns = DMLTemplates::get_pattern_templates();
        
        assert!(patterns.contains_key("memory_mapped"));
        assert!(patterns.contains_key("interrupt_controller"));
        assert!(patterns.contains_key("cpu"));
        assert!(patterns.contains_key("memory"));
        assert!(patterns.contains_key("bus_interface"));
    }

    #[test]
    fn test_pattern_template_execution() {
        let patterns = DMLTemplates::get_pattern_templates();
        let memory_mapped_fn = patterns.get("memory_mapped").unwrap();
        
        let config = json!({
            "base_address": 0x1000,
            "size": 0x100
        });
        
        let result = memory_mapped_fn("test_device", &config);
        assert!(result.is_ok());
        
        let device = result.unwrap();
        assert_eq!(device.name, "test_device");
    }

    #[test]
    fn test_indent_style_spaces() {
        let config = GenerationConfig {
            indent_style: IndentStyle::Spaces(2),
            ..Default::default()
        };
        
        let context = GenerationContext {
            device_name: "test".to_string(),
            namespace: "test".to_string(),
            imports: vec![],
            templates: vec![],
            config,
        };
        
        let generator = DMLGenerator::new(context);
        let indent = generator.get_indent();
        assert_eq!(indent, "  "); // 2 spaces
    }

    #[test]
    fn test_indent_style_tabs() {
        let config = GenerationConfig {
            indent_style: IndentStyle::Tabs,
            ..Default::default()
        };
        
        let context = GenerationContext {
            device_name: "test".to_string(),
            namespace: "test".to_string(),
            imports: vec![],
            templates: vec![],
            config,
        };
        
        let generator = DMLGenerator::new(context);
        let indent = generator.get_indent();
        assert_eq!(indent, "\t"); // tab character
    }
}