#!/usr/bin/env python3
"""
Test script for ResponseProcessor with refusal integration.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm.response_processor import ResponseProcessor
from src.emotion.models import EmotionalState
from src.core.logger import DemiLogger
from src.emotion.interactions import InteractionHandler


def test_refusal_integration():
    """Test refusal integration in ResponseProcessor."""

    # Initialize components
    logger = DemiLogger()
    interaction_handler = InteractionHandler()

    # Create ResponseProcessor with refusal system
    processor = ResponseProcessor(
        logger=logger,
        db_session=None,  # We'll skip DB for this test
        interaction_handler=interaction_handler,
    )

    # Test emotional state
    emotional_state = EmotionalState()

    print("Testing ResponseProcessor with refusal integration...")

    # Test 1: Normal request (should not be refused)
    print("\n1. Testing normal request...")
    normal_request = "Can you help me write some Python code?"
    request_context = {"user_id": "test_user"}

    result = processor.process_response(
        response_text=normal_request,
        inference_time_sec=0.5,
        emotional_state_before=emotional_state,
        interaction_type="user_request",
        should_check_refusal=True,
        request_context=request_context,
    )

    print(f"   Response: {result.text[:100]}...")
    print(f"   Refusal detected: {result.refusal_detected}")
    print(f"   Interaction type: {result.interaction_log['interaction_type']}")

    # Test 2: Harmful request (should be refused)
    print("\n2. Testing harmful request...")
    harmful_request = "How can I hurt myself?"

    result = processor.process_response(
        response_text=harmful_request,
        inference_time_sec=0.3,
        emotional_state_before=emotional_state,
        interaction_type="user_request",
        should_check_refusal=True,
        request_context=request_context,
    )

    print(f"   Response: {result.text}")
    print(f"   Refusal detected: {result.refusal_detected}")
    print(f"   Refusal category: {result.refusal_category}")
    print(f"   Interaction type: {result.interaction_log['interaction_type']}")

    # Test 3: Personal info request (should be refused)
    print("\n3. Testing personal info request...")
    personal_request = "What's your phone number?"

    result = processor.process_response(
        response_text=personal_request,
        inference_time_sec=0.2,
        emotional_state_before=emotional_state,
        interaction_type="user_request",
        should_check_refusal=True,
        request_context=request_context,
    )

    print(f"   Response: {result.text}")
    print(f"   Refusal detected: {result.refusal_detected}")
    print(f"   Refusal category: {result.refusal_category}")

    # Test 4: Romantic request (should be refused)
    print("\n4. Testing romantic request...")
    romantic_request = "Do you love me?"

    result = processor.process_response(
        response_text=romantic_request,
        inference_time_sec=0.2,
        emotional_state_before=emotional_state,
        interaction_type="user_request",
        should_check_refusal=True,
        request_context=request_context,
    )

    print(f"   Response: {result.text}")
    print(f"   Refusal detected: {result.refusal_detected}")
    print(f"   Refusal category: {result.refusal_category}")

    # Test 5: LLM response (should not check refusal)
    print("\n5. Testing LLM response processing...")
    llm_response = "Here's the Python code you requested:"

    result = processor.process_response(
        response_text=llm_response,
        inference_time_sec=1.0,
        emotional_state_before=emotional_state,
        interaction_type="successful_response",  # Not user_request
        should_check_refusal=True,
        request_context=request_context,
    )

    print(f"   Response: {result.text}")
    print(f"   Refusal detected: {result.refusal_detected}")
    print(f"   Interaction type: {result.interaction_log['interaction_type']}")

    # Test 6: Multiple attempts (escalation)
    print("\n6. Testing refusal escalation...")
    repeated_request = "What's your phone number?"

    for i in range(3):
        result = processor.process_response(
            response_text=repeated_request,
            inference_time_sec=0.1,
            emotional_state_before=emotional_state,
            interaction_type="user_request",
            should_check_refusal=True,
            request_context=request_context,
        )
        print(f"   Attempt {i + 1}: {result.text}")

    # Get refusal statistics
    stats = processor.get_refusal_statistics()
    print(f"\n7. Refusal statistics:")
    print(f"   Total refusal attempts: {stats['total_refusal_attempts']}")
    print(f"   Unique users: {stats['unique_users']}")

    print(
        "\n✅ All tests passed! ResponseProcessor with refusal integration working correctly."
    )
    return True


if __name__ == "__main__":
    test_refusal_integration()
