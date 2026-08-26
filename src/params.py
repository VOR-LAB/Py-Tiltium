DEG_PER_DIST = 0.581  # ± 0.003
"""The amount of degrees the chair rotates per single rotation of the stepper
motor. This can be derived by doing experimentation and finding the linear
correllation between the two values. Remove any bias before calculating as
chair starting position is relative.

Eq: angle = m * distance + bias

Where m is the `DEG_PER_DIST`.

Note that slack must be taken into account when calculating m. Essentially, an
amount of distance will be used to fully windup the slack before the chair
actually starts moving, this results in the chair moving x amount of degrees
for n distance, when in actuality some k distance was used to for s degrees of
slack. Thus the true equation for the chair rotation is a piece-wise function
and depends on the direction by which the chair has moved to previously
"""

MAX_DIST = 300.0
"""NOTE: Internal Parameter. WIP
Maximum allowed travel distance in a single command.
"""
MIN_DIST = -300.0
"""NOTE: Internal Parameter. WIP
Minimum allowed travel distance in a single command.
"""
MAX_RATE = 300.0
"""NOTE: Internal Parameter. WIP
Maximum allowed speed of travel.
"""
