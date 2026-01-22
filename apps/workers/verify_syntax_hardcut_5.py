
import sys
import os

# Add src to path
sys.path.append('/Users/younes/dev/autodj/apps/workers')

try:
    from src.mixing.draft_transition_generator import _generate_hard_cut_with_plan_enhanced
    print("Successfully imported Hard Cut function")
except ImportError as e:
    print(f"ImportError: {e}")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
except Exception as e:
    print(f"Error: {e}")
