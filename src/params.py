DEG_PER_DIST = 0.560 # ± 0.003
"""The amount of degrees the chair rotates per single rotation of the stepper
motor. This can be derived by doing experimentation and finding the linear
correllation between the two values. Remove any bias before calculating as
chair starting position is relative.

Eq: angle = m * distance + bias

Where m is the `DEG_PER_DIST`.
"""

MAX_DIST = 300.0
"""NOTE: Internal Parameter. WIP
Maximum allowed travle distance in a single command.
"""
MIN_DIST = -300.0
"""NOTE: Internal Parameter. WIP
Minimum allowed travle distance in a single command.
"""
MAX_RATE = 300.0
"""NOTE: Internal Parameter. WIP
Maximum allowed speed of travle.
""" 
