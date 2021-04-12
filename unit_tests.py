# Users
# 1. getOwnership: check that indeed it returns the objects the user is supposed to own.
#    Maybe we can do that only using object ids to avoid clutter.
# 2. cedeOwnership: check that it creates the proper notification. Check that it returns the specific objects the
#    user is not supposed to own. Check if fails gracefully when there are no objects owned with the given ids.
# 3. cedeOwnership confirmation: check the Yes and No replies from a heir.
# 4. cedeOwnershipAll: 


# Lenses
# - Queries
# 1. Select lenses for a user without any private access.
# 2. Select lenses for a user with direct private access.
# 3. Select lenses for a user with access via his groups.
# 4. Select lenses for a user with both direct and group access (on different, but also some same lenses).
