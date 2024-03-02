import os, sys
import unittest
import numpy as np
import django
from astropy import units as u
from astropy.coordinates import SkyCoord

base_dir = '../../'
sys.path.append(base_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroups, Lenses
#from django.forms.models import model_to_dict
#from guardian.shortcuts import assign_perm

class users(unittest.TestCase):
    """
    unittest class for basic user-based tests
    """
    def setUp(self):
        self.username = 'testuser'

    def test_a_add_user(self):
        """
        Test to add a user and check they are in the database
        """
        user  = Users(username=self.username)
        user.save()
        all_users = Users.objects.all().values_list('username', flat=True)
        self.assertIn(self.username, all_users)

    def test_b_delete_user(self):
        """
        Test to delete a user and check they are no longer in the database
        """
        user = Users.objects.filter(username=self.username)
        user.delete()
        all_users = Users.objects.all().values_list('username', flat=True)
        self.assertNotIn(self.username, all_users)

class lenses(unittest.TestCase):
    """
    unittest class for basic lens-based tests
    """
    def setUp(self):
        """
        setting up global variables for the tests
        """
        ras = np.random.uniform(0, 360, 2)
        decs = np.random.uniform(-90, 90, 2)
        cs = [SkyCoord(ra=ras[i]*u.degree, dec=decs[i]*u.degree, frame='icrs') for i in range(len(ras))]
        Jnames = ['J'+c.to_string('hmsdms') for c in cs]

        #this will be a public lens associated to user1
        self.ra1 = ras[0]
        self.dec1 = decs[0]
        self.name1 = Jnames[0]
        self.ra1 = 207.54991004332456 
        self.dec1 = 63.956814406428975
        self.name1 = 'J13h50m11.9784s +63d57m24.5319s'

        #this will be a private lens associated to user1
        self.ra2 = ras[1]
        self.dec2 = decs[1]
        self.name2 = Jnames[1]
        self.ra2 = 247.18738542693987 
        self.dec2 = -54.64928375016883 
        self.name2 = 'J16h28m44.9725s -54d38m57.4215s'

        self.username1 = 'testuser1'
        self.username2 = 'testuser2'
        

    def test_a_add_public_lens(self):
        """
        Test to add a lens to the database. First create a user and then add the lens.
        """
        #first see if our test user already exists in the database or not
        if self.username1 not in Users.objects.all().values_list('username', flat=True):
            user1  = Users(username=self.username1)
            user1.save()
        user1 = Users.objects.get(username=self.username1)

        lens = Lenses(ra=self.ra1, dec=self.dec1, name=self.name1, access_level='public', owner=user1)
        lens.save()
        print('added public lens:', self.ra1, self.dec1, self.name1)
        all_lenses = Lenses.objects.all().values_list('name', flat=True)
        self.assertIn(self.name1, all_lenses)

    def test_b_check_len_isOwner(self):
        """
        Test to check the isOwner attribute for a lens
        """ 
        lens = Lenses.objects.get(name=self.name1)
        user1 = Users.objects.get(username=self.username1)
        print('user1 id is:', user1.id)
        print('lens is:', lens)
        print('lens owner id is', lens.owner_id)
        self.assertTrue(lens.isOwner(user1.id))

    def test_c_add_private_lens(self):
        """
        Test to add a private lens to the database. First create a user and then add the lens.
        """
        #first see if our test user already exists in the database or not
        if self.username1 not in Users.objects.all().values_list('username', flat=True):
            user1  = Users(username=self.username1)
            user1.save()
        user1 = Users.objects.get(username=self.username1)

        lens = Lenses(ra=self.ra2, dec=self.dec2, name=self.name2, access_level='private', owner=user1)
        lens.save()
        print('added private lens:', self.ra2, self.dec2, self.name2)
        all_lenses = Lenses.objects.all().values_list('name', flat=True)
        self.assertIn(self.name1, all_lenses)


    def test_d_access_to_public_lens(self):
        """
        Check that user2 has access to public lenses
        """
        #first see if our test user already exists in the database or not
        if self.username2 not in Users.objects.all().values_list('username', flat=True):
            user2  = Users(username=self.username2)
            user2.save()
        user2 = Users.objects.get(username=self.username2)

        access_lenses = Lenses.accessible_objects.all(user2).values_list('name', flat=True)
        self.assertIn(self.name1, access_lenses)


    def test_e_access_to_private_lens(self):
        """
        Check that user2 has no access to private lens
        """
        #first see if our test user already exists in the database or not
        if self.username2 not in Users.objects.all().values_list('username', flat=True):
            user2  = Users(username=self.username2)
            user2.save()
        user2 = Users.objects.get(username=self.username2)

        access_lenses = Lenses.accessible_objects.all(user2).values_list('name', flat=True)
        self.assertNotIn(self.name2, access_lenses)

    def test_f_delete_lenses(self):
        """
        Check that lenses can be deleted
        (HERE WE NEED MORE COMPLEX TESTS ABOUT REQUIRING PERMISSION TO DELETE THE LENS)
        """
        #first see if our test user already exists in the database or not
        lens1 = Lenses.objects.get(name=self.name1)
        lens1.delete()
        lens2 = Lenses.objects.get(name=self.name2)
        lens2.delete()

        all_lenses = Lenses.objects.all().values_list('name', flat=True)
        lens1_deleted = self.name1 in all_lenses
        lens2_deleted = self.name2 in all_lenses

        self.assertEqual(lens1_deleted+lens2_deleted, 0)


    '''def test_delete_public_lens_as_nonowner(self):
        """
        Test to delete a lens from the database as the owner. Should be allowed.
        """
        WRITE ME

    def test_delete_public_lens_as_nonowner(self):
        """
        Test to delete a lens from the database not as the owner. Should fail!
        """
        WRITE ME'''



if __name__ == '__main__':
    unittest.main()