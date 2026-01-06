"""
Phase 10 End-to-End Demo.
Demonstrates the full pipeline:
Query -> Planner -> Executor (Vector + WASM) -> Signed Findings -> Verification.
"""

import logging
import sys

from cns_py.api.server import ResultVerifyRequest, verify_result_endpoint
from cns_py.crypto import signing
from cns_py.planner import Executor, Planner
from cns_py.vector.manager import IndexManager

# Setup simple logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("demo_phase10")


def run_demo():
    logger.info("=== Phase 10 Demo Start ===")

    # 1. Initialize Components
    logger.info("1. Initializing System...")
    # Using real manager (will use stub provider/memory index by default)
    index_manager = IndexManager()
    index_manager.startup()

    planner = Planner()
    executor = Executor(index_manager)

    # 2. Plan
    curr_query = "verify tls compliance for app_1"
    logger.info(f"2. User Query: '{curr_query}'")
    plan = planner.plan(curr_query)
    logger.info(f"   Generated Plan: {len(plan.steps)} steps")
    for i, s in enumerate(plan.steps):
        logger.info(f"     Step {i}: {s.step_type} ({s.description})")

    # 3. Execute
    logger.info("3. Executing Plan...")
    findings = executor.execute(plan)

    # Inspect Results
    logger.info(f"   Execution Complete. Results: {len(findings.results)}")

    for res in findings.results:
        if res.step_type == "wasm_rule":
            logger.info(f"     [WASM Output] Rule: {res.rule_output.get('rule', 'unknown')}")
            # The placeholder rule returns "findings" inside rule_output
            # Check debug output from test run to see structure:
            # {"findings": [{"kind": "...", ...}]} is likely the RAW output from WASM.
            # Executor puts it in res.rule_output based on execute_rule return.
            if "findings" in res.rule_output:
                for f in res.rule_output["findings"]:
                    logger.info(f"       Finding: {f['message']}")

    # 4. Sign Findings
    logger.info("4. Signing Findings...")
    # Convert Findings model to dict for signing
    findings_dict = findings.dict()

    priv_key = signing.generate_private_key()
    pub_key = priv_key.public_key()
    pub_hex = pub_key.public_bytes(
        encoding=signing.serialization.Encoding.Raw, format=signing.serialization.PublicFormat.Raw
    ).hex()

    signature = signing.sign_claim(findings_dict, priv_key)
    logger.info(f"   Signature: {signature[:16]}...")

    # 5. Verify (Simulate API Call)
    logger.info("5. Verifying via API Endpoint...")
    req = ResultVerifyRequest(result_payload=findings_dict, signature=signature, public_key=pub_hex)

    verify_resp = verify_result_endpoint(req)
    if verify_resp.valid:
        logger.info(f"   ✅ Verification SUCCESS. Hash: {verify_resp.result_hash}")
    else:
        logger.error(f"   ❌ Verification FAILED. Reason: {verify_resp.reason}")
        sys.exit(1)

    logger.info("=== Phase 10 Demo Complete ===")


if __name__ == "__main__":
    run_demo()
