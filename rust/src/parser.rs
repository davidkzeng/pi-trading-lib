use std::collections::HashMap;
use std::io::Write;
use std::iter::{Iterator, Peekable};

pub struct Parser<'a> {
    arg_map: HashMap<&'a str, Arg<'a>>,
}

impl<'a> Parser<'a> {
    pub fn new() -> Self {
        Parser {
            arg_map: HashMap::new(),
        }
    }

    pub fn arg(mut self, arg: Arg<'a>) -> Self {
        let existing = self.arg_map.insert(arg.name, arg);
        assert!(existing.is_none());
        self
    }

    pub fn apply<F: FnOnce(Self) -> Self>(self, f: F) -> Self {
        f(self)
    }

    pub fn create(self) -> Result<Self, String> {
        self.arg_map.iter().try_for_each(|(_k, v)| v.check_spec())?;
        Ok(self)
    }

    pub fn print_help<W: Write>(&self, writer: W) {}

    pub fn parse_args<I: Iterator<Item = &'a String>>(mut self, args: I) -> Result<Self, String> {
        let mut args_iter = args.peekable();
        args_iter.next().unwrap();
        while let Some(arg_name) = args_iter.next() {
            if arg_name.len() <= 2 || &arg_name[..2] != "--" {
                return Err("Arguments must start with '--': ".to_owned() + arg_name);
            }
            if let Some(arg) = self.arg_map.get_mut(&arg_name[2..]) {
                arg.consume(&mut args_iter)?;
            } else {
                return Err("Unrecognized argument: ".to_owned() + arg_name);
            }
        }
        Ok(self)
    }

    pub fn get_str_arg(&self, arg_name: &str) -> Result<&'a str, String> {
        if let Some(arg) = self.arg_map.get(arg_name) {
            arg.get_str()
        } else {
            Err("Unrecognized argument: ".to_owned() + arg_name)
        }
    }
}

#[derive(PartialEq)]
enum ArgType {
    Flag,
    Value,
}

enum ArgValue<'a> {
    None,
    Str(&'a str),
    StrVec(Vec<&'a str>),
}

pub struct Arg<'a> {
    name: &'a str,
    arg_type: ArgType,
    default: ArgValue<'a>,
    required: bool,
    multiple: bool,
    // parse time
    consumed: u64,
    value: ArgValue<'a>,
}

impl<'a> Arg<'a> {
    // Builder

    pub fn with_name(name: &'a str) -> Self {
        Arg {
            name,
            arg_type: ArgType::Flag,
            default: ArgValue::None,
            required: false,
            multiple: false,
            consumed: 0,
            value: ArgValue::None,
        }
    }

    pub fn takes_value(mut self) -> Self {
        self.arg_type = ArgType::Value;
        self
    }

    pub fn default(mut self, default: &'a str) -> Self {
        self.default = ArgValue::Str(default);
        self
    }

    pub fn required(mut self) -> Self {
        self.required = true;
        self
    }

    pub fn multiple(mut self) -> Self {
        self.multiple = true;
        self
    }

    pub fn check_spec(&self) -> Result<(), String> {
        let has_default = match &self.default {
            ArgValue::None => true,
            _ => false,
        };

        if has_default && self.arg_type == ArgType::Flag {
            return Err("Bad spec".to_owned());
        }
        if has_default && self.required {
            return Err("Bad Spec".to_owned());
        }
        if self.multiple && self.arg_type == ArgType::Flag {
            return Err("Bad spec".to_owned());
        }
        Ok(())
    }

    pub fn consume<I>(&mut self, iter: &mut Peekable<I>) -> Result<(), String>
    where
        I: Iterator<Item = &'a String>,
    {
        if self.arg_type == ArgType::Flag {
            return Ok(());
        }

        while let Some(token) = iter.peek() {
            if self.consumed == 1 && !self.multiple {
                // maybe we should exit if this is the second try at consuming?
                break;
            }
            if token.len() >= 2 && &token[..2] == "--" {
                break;
            }

            if !self.multiple {
                self.value = ArgValue::Str(token.as_str())
            } else {
                match &mut self.value {
                    ArgValue::None => {
                        self.value = ArgValue::StrVec(vec![token.as_str()]);
                    }
                    ArgValue::StrVec(values) => {
                        values.push(token.as_str());
                    }
                    _ => panic!(),
                }
            }
            self.consumed += 1;
            iter.next();
        }

        if self.consumed == 0 {
            Err("No values to parse for: ".to_owned() + self.name)
        } else {
            Ok(())
        }
    }

    fn get_value(&self) -> &ArgValue<'a> {
        match self.value {
            ArgValue::None => &self.default,
            _ => &self.value,
        }
    }

    // Getters
    //
    pub fn get_str(&self) -> Result<&'a str, String> {
        match self.get_value() {
            ArgValue::Str(s) => Ok(s),
            _ => Err(String::from("sadge")),
        }
    }
}
