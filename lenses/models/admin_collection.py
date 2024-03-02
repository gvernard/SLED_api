import inspect

from django.db import models
from django.urls import reverse

from gm2m import GM2MField
from gm2m.deletion import DO_NOTHING

from . import SingleObject




class creationManager(models.Manager):
    def create(self, **col_data):
        objects = col_data.pop('myitems')
        try:
            wrong_type = []
            for obj in objects:
                if obj._meta.model.__name__ != col_data['item_type']:
                    wrong_type.append(obj)
            assert (len(wrong_type)==0),"The following items are not of the same type as the collection type: "
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise

        col = super().create(**col_data)
        col.myitems.add(*objects)
        return col


class AdminCollection(models.Model):
    myitems = GM2MField('Lenses','Collection',on_delete=DO_NOTHING)
    ItemTypeChoices = (
        ('Lenses','Lenses'),
        ('Collection','Collection'),
        ('Users','Users'),
        ('Imaging','Imaging'),
        ('Spectrum','Spectrum'),
        ('Redshift','Redshift'),
        ('Catalogue','Catalogue'),
        ('Scores','Scores'),
        ('Models','Models')
    )
    item_type = models.CharField(max_length=100,
                                 choices=ItemTypeChoices,
                                 help_text="The type of items that should be in the collection.")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = creationManager()

    
    class Meta():
        db_table = "admin_collection"
        verbose_name = "admin collection"
        verbose_name_plural = "admin collections"
        ordering = ["created_at"]


    def get_absolute_url(self):
        return reverse('sled_admin_collections:admin-collections-detail',kwargs={'pk':self.id})

