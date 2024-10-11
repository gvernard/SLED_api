from rest_framework import serializers, fields
from lenses.models import Users, SledGroup, Lenses, DataBase, Imaging, Spectrum, Catalogue, Paper, Collection
from django.contrib.sites.models import Site
from django.db.models import F


class LensDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lenses
        fields = ['ra',
                  'dec',
                  'name',
                  'alt_name',
                  'flag',
                  'score',
                  'image_sep',
                  'info',
                  'n_img',
                  'image_conf',
                  'lens_type',
                  'source_type',
                  'contaminant_type',
                  'mugshot']
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        site = Site.objects.get_current()
        mugshot_url = 'https://' + site.domain + ret['mugshot']
        ret['mugshot'] = mugshot_url
        return ret
        


class ImagingDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imaging
        fields = ['instrument',
                  'date_taken',
                  'future',
                  'info',
                  'exposure_time',
                  'pixel_size',
                  'image'
                  ]
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        site = Site.objects.get_current()
        image_url = 'https://' + site.domain + ret['image']
        ret['image'] = image_url
        return ret


class PaperDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = ['year',
                  'first_author',
                  'title',
                  'cite_as',
                  ]
        



    
class LensDownSerializerAll(serializers.ModelSerializer):
    imaging = ImagingDownSerializer(many=True,read_only=True)
    papers = PaperDownSerializer(many=True,read_only=True)
    #genericimage
    #spectrum
    #catalogue
    #redshift
    #models
    
    class Meta:
        model = Lenses
        fields = ['ra',
                  'dec',
                  'name',
                  'alt_name',
                  'flag',
                  'score',
                  'image_sep',
                  'info',
                  'n_img',
                  'image_conf',
                  'lens_type',
                  'source_type',
                  'contaminant_type',
                  'mugshot',
                  'imaging',
                  'genericimage',
                  'spectrum',
                  'catalogue',
                  'redshift',
                  'papers']

        
    def __init__(self, *args, **kwargs):
        # Instantiate the superclass normally
        super(LensDownSerializerAll, self).__init__(*args, **kwargs)

        fields_to_remove = self.context.get('fields_to_remove')
        for field in fields_to_remove:
            self.fields.pop(field)

            
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        site = Site.objects.get_current()
        mugshot_url = 'https://' + site.domain + ret['mugshot']
        ret['mugshot'] = mugshot_url

        
        for paper in instance.papers.all():
            print(instance.papers(manager='objects').all().annotate(discovery=F('paperlensconnection__discovery'),
                                                    model=F('paperlensconnection__model'),
                                                    classification=F('paperlensconnection__classification'), #redshift=F('paperlensconnection__redshift')
                                                    ))


        return ret

    
