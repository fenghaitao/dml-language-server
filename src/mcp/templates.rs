//! DML code templates for common patterns

use anyhow::Result;
use std::collections::HashMap;

use super::generation::{DeviceSpec, BankSpec, RegisterSpec, FieldSpec, MethodSpec, ParameterSpec, InterfaceSpec};

/// Built-in DML templates and patterns
pub struct DMLTemplates;

impl DMLTemplates {
    /// Get basic device template
    pub fn basic_device(name: &str, device_type: &str) -> DeviceSpec {
        let base_template = match device_type {
            "cpu" => Some("cpu_device".to_string()),
            "memory" => Some("memory_device".to_string()),
            "peripheral" => Some("peripheral_device".to_string()),
            _ => Some("base_device".to_string()),
        };
        
        DeviceSpec {
            name: name.to_string(),
            base_template,
            documentation: Some(format!("Generated {} device", device_type)),
            banks: vec![],
            interfaces: vec![],
            methods: vec![],
            dependencies: vec![],
        }
    }
    
    /// Get memory-mapped device template
    pub fn memory_mapped_device(name: &str, _base_address: u64, _size: u64) -> DeviceSpec {
        let mut device = Self::basic_device(name, "peripheral");
        
        // Add memory bank
        device.banks.push(BankSpec {
            name: "registers".to_string(),
            documentation: Some("Memory-mapped registers".to_string()),
            registers: vec![
                RegisterSpec {
                    name: "control".to_string(),
                    size: 4,
                    offset: Some("0x00".to_string()),
                    documentation: Some("Control register".to_string()),
                    fields: vec![
                        FieldSpec {
                            name: "enable".to_string(),
                            bits: "0".to_string(),
                            access: Some("rw".to_string()),
                            documentation: Some("Enable bit".to_string()),
                        },
                        FieldSpec {
                            name: "reset".to_string(),
                            bits: "1".to_string(),
                            access: Some("rw".to_string()),
                            documentation: Some("Reset bit".to_string()),
                        },
                    ],
                    methods: vec![],
                },
                RegisterSpec {
                    name: "status".to_string(),
                    size: 4,
                    offset: Some("0x04".to_string()),
                    documentation: Some("Status register".to_string()),
                    fields: vec![
                        FieldSpec {
                            name: "ready".to_string(),
                            bits: "0".to_string(),
                            access: Some("ro".to_string()),
                            documentation: Some("Ready status".to_string()),
                        },
                        FieldSpec {
                            name: "error".to_string(),
                            bits: "1".to_string(),
                            access: Some("ro".to_string()),
                            documentation: Some("Error status".to_string()),
                        },
                    ],
                    methods: vec![],
                },
            ],
        });
        
        // Add standard interfaces
        device.interfaces.push(InterfaceSpec {
            name: "io_memory".to_string(),
        });
        
        device
    }
    
    /// Get interrupt controller template
    pub fn interrupt_controller(name: &str, num_irqs: u32) -> DeviceSpec {
        let mut device = Self::basic_device(name, "peripheral");
        
        device.banks.push(BankSpec {
            name: "registers".to_string(),
            documentation: Some("Interrupt controller registers".to_string()),
            registers: vec![
                RegisterSpec {
                    name: "irq_enable".to_string(),
                    size: 4,
                    offset: Some("0x00".to_string()),
                    documentation: Some("Interrupt enable register".to_string()),
                    fields: vec![],
                    methods: vec![
                        MethodSpec {
                            name: "write".to_string(),
                            parameters: vec![
                                ParameterSpec {
                                    name: "value".to_string(),
                                    param_type: "uint32".to_string(),
                                }
                            ],
                            return_type: None,
                            body: Some("enabled_irqs = value;".to_string()),
                            documentation: Some("Enable/disable interrupts".to_string()),
                        }
                    ],
                },
                RegisterSpec {
                    name: "irq_pending".to_string(),
                    size: 4,
                    offset: Some("0x04".to_string()),
                    documentation: Some("Pending interrupts register".to_string()),
                    fields: vec![],
                    methods: vec![
                        MethodSpec {
                            name: "read".to_string(),
                            parameters: vec![],
                            return_type: Some("uint32".to_string()),
                            body: Some("return pending_irqs;".to_string()),
                            documentation: Some("Read pending interrupts".to_string()),
                        }
                    ],
                },
            ],
        });
        
        device.interfaces.push(InterfaceSpec {
            name: "signal".to_string(),
        });
        
        device.methods.push(MethodSpec {
            name: "signal_raise".to_string(),
            parameters: vec![
                ParameterSpec {
                    name: "irq".to_string(),
                    param_type: "int".to_string(),
                }
            ],
            return_type: None,
            body: Some(format!(
                "if (irq >= 0 && irq < {}) {{\n        pending_irqs |= (1 << irq);\n        update_interrupt();\n    }}",
                num_irqs
            )),
            documentation: Some("Raise an interrupt".to_string()),
        });
        
        device
    }
    
    /// Get CPU device template
    pub fn cpu_device(name: &str, arch: &str) -> DeviceSpec {
        let mut device = Self::basic_device(name, "cpu");
        device.base_template = Some(format!("{}_cpu", arch));
        
        device.banks.push(BankSpec {
            name: "registers".to_string(),
            documentation: Some("CPU control registers".to_string()),
            registers: vec![
                RegisterSpec {
                    name: "pc".to_string(),
                    size: 8,
                    offset: Some("0x00".to_string()),
                    documentation: Some("Program counter".to_string()),
                    fields: vec![],
                    methods: vec![
                        MethodSpec {
                            name: "read".to_string(),
                            parameters: vec![],
                            return_type: Some("uint64".to_string()),
                            body: Some("return cpu.pc;".to_string()),
                            documentation: Some("Read program counter".to_string()),
                        },
                        MethodSpec {
                            name: "write".to_string(),
                            parameters: vec![
                                ParameterSpec {
                                    name: "value".to_string(),
                                    param_type: "uint64".to_string(),
                                }
                            ],
                            return_type: None,
                            body: Some("cpu.pc = value;".to_string()),
                            documentation: Some("Write program counter".to_string()),
                        }
                    ],
                },
            ],
        });
        
        device.interfaces.extend([
            InterfaceSpec { name: "processor".to_string() },
            InterfaceSpec { name: "cycle".to_string() },
            InterfaceSpec { name: "execute".to_string() },
        ]);
        
        device.methods.extend([
            MethodSpec {
                name: "init".to_string(),
                parameters: vec![],
                return_type: None,
                body: Some("// Initialize CPU state".to_string()),
                documentation: Some("Initialize the CPU".to_string()),
            },
            MethodSpec {
                name: "reset".to_string(),
                parameters: vec![],
                return_type: None,
                body: Some("// Reset CPU to initial state".to_string()),
                documentation: Some("Reset the CPU".to_string()),
            },
        ]);
        
        device
    }
    
    /// Get memory device template
    pub fn memory_device(name: &str, size_mb: u32) -> DeviceSpec {
        let mut device = Self::basic_device(name, "memory");
        
        device.banks.push(BankSpec {
            name: "memory".to_string(),
            documentation: Some(format!("{}MB memory bank", size_mb)),
            registers: vec![], // Memory devices typically don't have registers
        });
        
        device.interfaces.push(InterfaceSpec {
            name: "io_memory".to_string(),
        });
        
        device.methods.extend([
            MethodSpec {
                name: "read".to_string(),
                parameters: vec![
                    ParameterSpec {
                        name: "offset".to_string(),
                        param_type: "uint64".to_string(),
                    },
                    ParameterSpec {
                        name: "size".to_string(),
                        param_type: "int".to_string(),
                    }
                ],
                return_type: Some("uint64".to_string()),
                body: Some("return memory_read(offset, size);".to_string()),
                documentation: Some("Read from memory".to_string()),
            },
            MethodSpec {
                name: "write".to_string(),
                parameters: vec![
                    ParameterSpec {
                        name: "offset".to_string(),
                        param_type: "uint64".to_string(),
                    },
                    ParameterSpec {
                        name: "value".to_string(),
                        param_type: "uint64".to_string(),
                    },
                    ParameterSpec {
                        name: "size".to_string(),
                        param_type: "int".to_string(),
                    }
                ],
                return_type: None,
                body: Some("memory_write(offset, value, size);".to_string()),
                documentation: Some("Write to memory".to_string()),
            },
        ]);
        
        device
    }
    
    /// Get bus interface template
    pub fn bus_interface_device(name: &str, _bus_width: u32) -> DeviceSpec {
        let mut device = Self::basic_device(name, "peripheral");
        
        device.banks.push(BankSpec {
            name: "config".to_string(),
            documentation: Some("Bus interface configuration".to_string()),
            registers: vec![
                RegisterSpec {
                    name: "bus_config".to_string(),
                    size: 4,
                    offset: Some("0x00".to_string()),
                    documentation: Some("Bus configuration register".to_string()),
                    fields: vec![
                        FieldSpec {
                            name: "width".to_string(),
                            bits: "7:0".to_string(),
                            access: Some("rw".to_string()),
                            documentation: Some("Bus width".to_string()),
                        },
                        FieldSpec {
                            name: "endian".to_string(),
                            bits: "8".to_string(),
                            access: Some("rw".to_string()),
                            documentation: Some("Endianness (0=little, 1=big)".to_string()),
                        },
                    ],
                    methods: vec![],
                },
            ],
        });
        
        device.interfaces.extend([
            InterfaceSpec { name: "io_memory".to_string() },
            InterfaceSpec { name: "signal".to_string() },
        ]);
        
        device
    }
    
    /// Get common design patterns
    pub fn get_pattern_templates() -> HashMap<String, Box<dyn Fn(&str, &serde_json::Value) -> Result<DeviceSpec>>> {
        let mut patterns: HashMap<String, Box<dyn Fn(&str, &serde_json::Value) -> Result<DeviceSpec>>> = HashMap::new();
        
        patterns.insert("memory_mapped".to_string(), Box::new(|name: &str, config: &serde_json::Value| {
            let base_addr = config["base_address"].as_u64().unwrap_or(0);
            let size = config["size"].as_u64().unwrap_or(0x1000);
            Ok(Self::memory_mapped_device(name, base_addr, size))
        }));
        
        patterns.insert("interrupt_controller".to_string(), Box::new(|name: &str, config: &serde_json::Value| {
            let num_irqs = config["num_irqs"].as_u64().unwrap_or(32) as u32;
            Ok(Self::interrupt_controller(name, num_irqs))
        }));
        
        patterns.insert("cpu".to_string(), Box::new(|name: &str, config: &serde_json::Value| {
            let arch = config["architecture"].as_str().unwrap_or("generic");
            Ok(Self::cpu_device(name, arch))
        }));
        
        patterns.insert("memory".to_string(), Box::new(|name: &str, config: &serde_json::Value| {
            let size_mb = config["size_mb"].as_u64().unwrap_or(64) as u32;
            Ok(Self::memory_device(name, size_mb))
        }));
        
        patterns.insert("bus_interface".to_string(), Box::new(|name: &str, config: &serde_json::Value| {
            let bus_width = config["bus_width"].as_u64().unwrap_or(32) as u32;
            Ok(Self::bus_interface_device(name, bus_width))
        }));
        
        patterns
    }
}

/// Common DML code snippets
pub struct DMLSnippets;

impl DMLSnippets {
    /// Standard method implementations
    pub fn standard_read_method() -> MethodSpec {
        MethodSpec {
            name: "read".to_string(),
            parameters: vec![],
            return_type: Some("uint32".to_string()),
            body: Some("return val;".to_string()),
            documentation: Some("Read register value".to_string()),
        }
    }
    
    pub fn standard_write_method() -> MethodSpec {
        MethodSpec {
            name: "write".to_string(),
            parameters: vec![
                ParameterSpec {
                    name: "value".to_string(),
                    param_type: "uint32".to_string(),
                }
            ],
            return_type: None,
            body: Some("val = value;".to_string()),
            documentation: Some("Write register value".to_string()),
        }
    }
    
    pub fn init_method() -> MethodSpec {
        MethodSpec {
            name: "init".to_string(),
            parameters: vec![],
            return_type: None,
            body: Some("// Initialize register to default value\nval = 0;".to_string()),
            documentation: Some("Initialize register".to_string()),
        }
    }
    
    /// Common field patterns
    pub fn enable_field() -> FieldSpec {
        FieldSpec {
            name: "enable".to_string(),
            bits: "0".to_string(),
            access: Some("rw".to_string()),
            documentation: Some("Enable bit".to_string()),
        }
    }
    
    pub fn status_field() -> FieldSpec {
        FieldSpec {
            name: "status".to_string(),
            bits: "1:0".to_string(),
            access: Some("ro".to_string()),
            documentation: Some("Status field".to_string()),
        }
    }
    
    pub fn interrupt_field() -> FieldSpec {
        FieldSpec {
            name: "interrupt".to_string(),
            bits: "31".to_string(),
            access: Some("rw".to_string()),
            documentation: Some("Interrupt enable".to_string()),
        }
    }
}