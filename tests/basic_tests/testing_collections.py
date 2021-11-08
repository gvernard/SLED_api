import sys
import os
import django
import unittest

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, Lenses, Collection, ConfirmationTask, SledGroup
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError

# A user to own the collection
geo = Users.objects.get(username='gvernard')
fre = Users.objects.get(username='Fred')
cam = Users.objects.get(username='Cameron')
awe = SledGroup.objects.get(name="Awesome Users")
tdc = SledGroup.objects.get(name="TDCOSMO")


'''
############################# Testing the ugs_with_access and the uds_without_access functions #############################
#                 !!! testing_user_functions.py will need to be ran first to set up some permissions. !!!
pub = Lenses.objects.filter(access_level='PUB')[4:8]
pri = Lenses.accessible_objects.owned(cam).filter(access_level='PRI')[:7]

print('For public objects an empty list should be returned:')
out = Lenses.accessible_objects.with_access([geo,fre,cam],pub)
print(out)
out = Lenses.accessible_objects.without_access([geo,fre,cam],pub)
print(out)

print("With access:")
out = Lenses.accessible_objects.with_access([geo,fre,cam,awe,tdc],pri)
for mydict in out:
    print(mydict["object"],mydict["ugs"])

print("Without access:")
out = Lenses.accessible_objects.without_access([geo,fre,cam,awe,tdc],pri)
for mydict in out:
    print(mydict["object"],mydict["ugs"])
print()
print()
'''



############################# Testing a public collection #############################
class TestPublicCollection(unittest.TestCase):
    def setUp(self):
        mycollection = Collection(owner=geo,name="TheBest",access_level='PUB',description="The best collection of lenses to walk the earth.",item_type="Lenses")
        mycollection.save()
        pub = Lenses.objects.filter(access_level='PUB').order_by('ra')[4:8]
        mycollection.myitems = pub
        mycollection.save()
        self.mycollection = mycollection
        #print(mycollection.myitems.all())

    # Check 1: the user trying to add objects is not the owner of the collection
    def test_a_not_owner(self):
        pub2 = Lenses.objects.filter(access_level='PUB').order_by('ra')[8:10]
        with self.assertRaises(AssertionError):
            self.mycollection.addItems(cam,list(pub2))

    # Check 2: trying to add wrong item types, e.g. ConfirmationTasks, etc
    def test_b_wrong_type(self):
        task = ConfirmationTask.create_task(geo,Users.getAdmin(),'MakePrivate',{})
        with self.assertRaises(AssertionError):
            self.mycollection.addItems(geo,task)

    # Check 3: some items are already in the collection.
    def test_c_existing(self):
        pub3 = Lenses.objects.filter(access_level='PUB').order_by('ra')[6:9]
        with self.assertRaises(AssertionError):
            self.mycollection.addItems(geo,pub3)

    # Check 4: all new items are public -> success
    def test_d_all_public(self):
        pub4 = Lenses.objects.filter(access_level='PUB').order_by('ra')[10:11]
        print()
        print(pub4)
        self.assertEqual(self.mycollection.addItems(geo,pub4),"success")

    # Check 5: try to add private objects to a public collection
    def test_e_add_private_to_public(self):
        pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[:5]
        print()
        print('Owner: ',pri.values_list('owner__username',flat=True))
        print('Users with access:')
        for obj in pri:
            print(obj,obj.getUsersWithAccess(cam))
        with self.assertRaises(AssertionError):
            self.mycollection.addItems(geo,pri)
########################################################################################



############################# Testing a private collection #############################
class TestPrivateCollection(unittest.TestCase):
    def setUp(self):
        mycollection = Collection(owner=geo,name="Worst",access_level='PRI',description="Aliens invaded earth in 2019 in the form of a virus.",item_type="Lenses")
        mycollection.save()
        pub = Lenses.objects.filter(access_level='PUB').order_by('ra')[4:8]
        mycollection.myitems = pub
        mycollection.save()
        self.mycollection = mycollection

    # Check 1: try to add private objects without access for ALL the users
    def test_a_add_private_without_access(self):
        pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[3:4]
        print()
        print('Owner: ',pri.values_list('owner__username',flat=True))
        print('Users with access:')
        for obj in pri:
            print(obj,obj.getUsersWithAccess(cam))
        dict_to_compare = {"users_per_obj":[{"object":pri[0],"ugs":[geo]}],"groups_per_obj":[]}
        self.assertDictEqual(self.mycollection.addItems(geo,pri),dict_to_compare)

    # # Check 2: try to add private objects without access for ALL the users
    def test_b_add_private_not_all_with_access(self):
        geo.giveAccess(self.mycollection,fre) # Here giveAccess should return an error because Fred doesn't have access to items currently in the collection.
        pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[3:5]
        print()
        print('Owner: ',pri.values_list('owner__username',flat=True))
        print('Users with access:')
        for obj in pri:
            print(obj,obj.getUsersWithAccess(cam))
        dict_to_compare = {"users_per_obj":[{"object":pri[0],"ugs":[fre,geo]},{"object":pri[1],"ugs":[fre]}],"groups_per_obj":[]}
        self.assertDictEqual(self.mycollection.addItems(geo,pri),dict_to_compare)

    # Check 3: try to add private objects with access
    def test_c_add_private_with_access(self):
        pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[:1]
        print()
        print('Owner: ',pri.values_list('owner__username',flat=True))
        print('Users with access:')
        for obj in pri:
            print(obj,obj.getUsersWithAccess(cam))
        self.assertEqual(self.mycollection.addItems(geo,pri),"success")

    # Check 4: give Access to all users and add private objects
    def test_d_add_private_with_access_all(self):
        users_with_access = list(self.mycollection.getUsersWithAccess(geo))
        users_with_access.append(geo)
        pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[9:11]
        print()
        print('Owner: ',pri.values_list('owner__username',flat=True))
        cam.giveAccess(pri,users_with_access)
        print('Users with access:')
        for obj in pri:
            print(obj,obj.getUsersWithAccess(cam))
        print(self.mycollection.myitems.all())
        self.assertEqual(self.mycollection.addItems(geo,pri),"success")
        print(self.mycollection.myitems.all())
##################################################################################



############################# Testing removing items #############################
class TestRemoveItemFromCollection(unittest.TestCase):
    def setUp(self):
        mycollection = Collection(owner=geo,name="Worst",access_level='PRI',description="Aliens invaded earth in 2019 in the form of a virus.",item_type="Lenses")
        mycollection.save()
        pub = Lenses.objects.filter(access_level='PUB').order_by('ra')[4:8]
        mycollection.myitems = pub
        mycollection.save()
        self.mycollection = mycollection

    # Check 1: the user trying to remove objects is not the owner of the collection
    def test_a_not_owner(self):
        to_remove = list(self.mycollection.myitems.all())[-1:]
        with self.assertRaises(AssertionError):
            self.mycollection.removeItems(cam,to_remove) 
            
    # Check 2: remove item from the collection
    def test_b_remove_item(self):
        print()
        print(self.mycollection.myitems.all())
        to_remove = list(self.mycollection.myitems.all())[-1:]
        print(to_remove)
        self.assertEqual(self.mycollection.removeItems(geo,to_remove),"success")
        print(self.mycollection.myitems.all())

    # Check 3: attempt to remove items that are not in the collection
    def test_c_remove_items_not_in(self):
        to_remove = list(self.mycollection.myitems.all())[-1:]
        to_remove.append(Lenses.objects.filter(access_level='PUB').order_by('ra')[20])
        print()
        print(self.mycollection.myitems.all())
        print(to_remove)
        with self.assertRaises(AssertionError):
            self.mycollection.removeItems(geo,to_remove)
        print(self.mycollection.myitems.all())
##################################################################################




############################# Testing a private collection with Group access #############################
class TestGroupAccessCollection(unittest.TestCase):
    def setUp(self):
        mycollection = Collection(owner=geo,name="Average",access_level='PRI',description="You touch my tralala.",item_type="Lenses")
        mycollection.save()
        pub = Lenses.objects.filter(access_level='PUB').order_by('ra')[4:8]
        mycollection.myitems = pub
        mycollection.save()
        self.mycollection = mycollection

    # Check 1: try to add private objects without access for ALL the users
    def test_a_add_private_without_access(self):
        tdcosmo = SledGroup.objects.get(name='TDCOSMO')
        geo.giveAccess(self.mycollection,tdcosmo) # Here giveAccess should return an error because Fred doesn't have access to items currently in the collection.
        pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[:1]
        print()
        print('Owner: ',pri.values_list('owner__username',flat=True))
        print('Users/Groups with access:')
        for obj in pri:
            print(obj,obj.getUsersWithAccess(cam),obj.getGroupsWithAccess(cam))
        dict_to_compare = {"users_per_obj":[],"groups_per_obj":[{"object":pri[0],"ugs":[tdcosmo]}]}
        self.assertDictEqual(self.mycollection.addItems(geo,pri),dict_to_compare)


    # Check 2: give Access to all group users and add private objects
    def test_b_add_private_with_access(self):
        tdcosmo = SledGroup.objects.get(name='TDCOSMO')
        geo.giveAccess(self.mycollection,tdcosmo)
        groups_with_access = list(self.mycollection.getGroupsWithAccess(geo))
        pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[4:6]
        print('Owner: ',pri.values_list('owner__username',flat=True))
        cam.giveAccess(pri,groups_with_access) # Important: user 'gvernard' also gains access to the objects because he is in the TDcosmo group
        print('Users/Groups with access:')
        for obj in pri:
            print(obj,obj.getUsersWithAccess(cam),obj.getGroupsWithAccess(cam))
        self.assertEqual(self.mycollection.addItems(geo,pri),"success")
##########################################################################################################


        

def suite():
    """
        Gather all the tests from this module in a test suite.
    """
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestPublicCollection))
    test_suite.addTest(unittest.makeSuite(TestPrivateCollection))
    test_suite.addTest(unittest.makeSuite(TestRemoveItemFromCollection))
    test_suite.addTest(unittest.makeSuite(TestGroupAccessCollection))
    return test_suite



if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

