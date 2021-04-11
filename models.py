from django.db import models

class SingleObject(models.Model):
    owner_id = models.ForeignKey(Users,db_index=False,on_delete=models.CASCADE)
    # We need to learn more about the FOreignKey options. E.g. when a user is deleted, a cede_responsibility should be called, see SET()?
    created_at = models.DateField(auto_now_add=True)
    modified_at = models.DateField(auto_now=True)
    access_level =  EnumField(choices=[
      ('public', 'Public access'),
      ('private', 'Private access')
    ],help_text="Set the access to this object.")

    class Meta:
        abstract = True
        managed = False
        get_latest_by = ["modified_at","created_at"]

    def isOwner(user_id):
        if user_id == self.owner_id:
            return True
        else:
            return False

    def getOwnerInfo():

    def setOwner(user_id,other_user_id):
        if self.isOwner(user_id):
            # call cede_responsibility
        else:
            # cannot setOwner, user is not the owner

    def getModifiedAt():
        return self.modified_at

    def getCreatedAt():
        return self.created_at

    def getLink():


    # Function that require access_table query
    def setAccessLevel():

    def setAccess():

    def addToCollection():
        
    
        

class Lenses(SingleObject):
    ra
    dec
    name
    alt_name
    image_sep
    image_conf
    z_source
    z_lens
    lens_type
    source_type
    flag_confirmed
    flag_contaminant
    info
    discovered_at = models.DateField(help_text="The date when this object was discovered, or the discovery paper published.")

    class Meta(SingleObject.Meta):
        db_table = "lenses"
        ordering = ["ra"]
        unique_together = ["ra","dec"]
        constraints = [
            models.CheckConstraint(check=models.Q(ra__gte=18), name='ra_lte_180'),
        ]
        verbose_name = "lens"
        verbose_name_plural = "lenses"
