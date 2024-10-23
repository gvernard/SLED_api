from django.db import models
from django.apps import apps
from django.dispatch import receiver
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

from . import Users


class LimitsAndRoles(models.Model):
    user = models.OneToOneField(Users,on_delete=models.CASCADE,primary_key=True)

    ### Limits
    limit_total_owned = models.IntegerField(blank=False,
                                            default=1000,
                                            verbose_name="Total owned",
                                            help_text="The total number of items owned.",
                                            validators=[MinValueValidator(0,"This limit cannot be negative"),
                                                        MaxValueValidator(25000,"Wow, that's a lot of items owned, are you sure?")])
    limit_add_per_week = models.IntegerField(blank=False,
                                             default=100,
                                             verbose_name="Per week",
                                             help_text="The total number of items added in a week.",
                                             validators=[MinValueValidator(0,"This limit cannot be negative"),
                                                         MaxValueValidator(10000,"Wow, that's a lot of items to be added in a week, are you sure?")])

    ### Roles
    is_inspector = models.BooleanField(blank=False,
                                       default=False,
                                       verbose_name="Inspector",
                                       help_text="User inspector role.")
    is_admin = models.BooleanField(blank=False,
                                   default=False,
                                   verbose_name="Admin",
                                   help_text="User admin role.")
    is_super_admin = models.BooleanField(blank=False,
                                         default=False,
                                         verbose_name="SUPER admin",
                                         help_text="User SUPER admin role (can assign admins).")
    

    class Meta():
        db_table = "limits_and_roles"

    def __str__(self):
        return self.user.username + ' limit and role'

