"""
Rule Registry Module (Slice 11.2).
Manages loading rule manifests and executing rules via WASM sandbox.
"""
import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from cns_py.wasm import execute_rule

class RuleMetadata(BaseModel):
    id: str
    version: str
    description: str
    wasm_file: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class RuleRegistry:
    def __init__(self, manifest_path: Optional[str] = None):
        self.rules: Dict[str, RuleMetadata] = {}
        self.root_dir = ""
        
        if manifest_path:
             self.load_manifest(manifest_path)
        else:
            # Default auto-discovery relative to this file -> repo root -> rules/manifest.json
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            default_path = os.path.join(base, "rules", "manifest.json")
            if os.path.exists(default_path):
                self.load_manifest(default_path)
            else:
                pass # Empty registry if not found

    def load_manifest(self, path: str):
        self.root_dir = os.path.dirname(path)
        with open(path, "r") as f:
            data = json.load(f)
            for item in data:
                rule = RuleMetadata(**item)
                self.rules[rule.id] = rule

    def list_rules(self) -> List[RuleMetadata]:
        return list(self.rules.values())

    def get_rule(self, rule_id: str) -> Optional[RuleMetadata]:
        return self.rules.get(rule_id)

    def run_rule(self, rule_id: str, input_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a rule by ID.
        Raises ValueError if rule not found or binary missing.
        """
        rule = self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")
            
        # Locate binary
        # Try .wat first (since we are using placeholders), then .wasm
        bin_path = os.path.join(self.root_dir, rule.wasm_file)
        
        if not os.path.exists(bin_path):
            # Try to swap extension if defined as .wat but strictly looking for compiled or vice versa
            # But relying on manifest being truthful is better.
            raise ValueError(f"Rule binary not found at: {bin_path}")
            
        with open(bin_path, "rb") as f:
            rule_bytes = f.read()
            
        # Execute
        result = execute_rule(rule_bytes, input_context)
        return result
