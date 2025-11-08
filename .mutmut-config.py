"""
Mutation Testing Configuration - Knuth's Code Quality Verification

Mutation testing verifies that tests catch real bugs by:
1. Introducing small changes (mutations) to code
2. Running tests against mutated code
3. Verifying tests fail (kill the mutant)
4. Measuring mutation score = killed / total

Mathematical Analysis (Knuth):
- Mutation Score = K / (K + S + T)
  where K = killed, S = survived, T = timeout
- Target: > 80% mutation score
- Perfect score (100%) often impractical

Tool: mutmut (Python mutation testing)
"""

def pre_mutation(context):
    """
    Hook called before each mutation

    Can skip mutations based on context
    """
    # Skip test files themselves
    if 'tests/' in context.filename:
        context.skip = True

    # Skip __init__ files (usually just imports)
    if context.filename.endswith('__init__.py'):
        context.skip = True

    # Skip configuration files
    if 'config' in context.filename.lower():
        context.skip = True


def post_mutation(context):
    """
    Hook called after each mutation

    Can analyze results, log, etc.
    """
    pass
