# Users
# 1. getOwnership: check that indeed it returns the objects the user is supposed to own.
#    Maybe we can do that only using object ids to avoid clutter.
# 2. cedeOwnership: check that it creates the proper notification. Check that it returns the specific objects the
#    user is not supposed to own. Check if fails gracefully when there are no objects owned with the given ids.
# 3. cedeOwnership confirmation: check the Yes and No replies from a heir.
# 4. cedeOwnershipAll: 
