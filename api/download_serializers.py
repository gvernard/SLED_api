from rest_framework import serializers, fields
from lenses.models import Users, SledGroup, Lenses, DataBase, Imaging, Spectrum, Catalogue, Paper, Collection, PaperLensConnection, GenericImage, Redshift
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
                  'mugshot',
                  'access_level']
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        #site = Site.objects.get_current()
        #mugshot_url = 'https://' + site.domain + ret['mugshot']
        #ret['mugshot'] = mugshot_url
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
                  'band',
                  'image'
                  ]
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        site = Site.objects.get_current()
        image_url = 'https://' + site.domain + ret['image']
        ret['image'] = image_url
        return ret


class SpectrumDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spectrum
        fields = ['instrument',
                  'date_taken',
                  'future',
                  'info',
                  'lambda_min',
                  'lambda_max',
                  'exposure_time',
                  'resolution',
                  'image'
                  ]
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        site = Site.objects.get_current()
        image_url = 'https://' + site.domain + ret['image']
        ret['image'] = image_url
        return ret


class CatalogueDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalogue
        fields = ['instrument',
                  'date_taken',
                  'future',
                  'info',
                  'radet',
                  'decdet',
                  'mag',
                  'Dmag',
                  'distance',
                  'band'
                  ]
        

class GenericImageDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericImage
        fields = ['name',
                  'info',
                  'image'
                  ]
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        site = Site.objects.get_current()
        image_url = 'https://' + site.domain + ret['image']
        ret['image'] = image_url
        return ret


class RedshiftDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Redshift
        fields = ['value',
                  'dvalue_min',
                  'dvalue_max',
                  'tag',
                  'method',
                  'info'
                  ]
        

class PaperDownSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Paper
        fields = ['year',
                  'first_author',
                  'title',
                  'cite_as',
                  ]
        


        


    
class LensDownSerializerAll(serializers.ModelSerializer):
    imaging = serializers.SerializerMethodField()
    spectrum = serializers.SerializerMethodField()
    catalogue = serializers.SerializerMethodField()
    redshift = RedshiftDownSerializer(many=True,read_only=True)
    papers = PaperDownSerializer(many=True,read_only=True)
    genericimage = GenericImageDownSerializer(many=True,read_only=True)
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
                  'access_level',
                  'imaging',
                  'genericimage',
                  'spectrum',
                  'catalogue',
                  'redshift',
                  'papers',
                  ]

    def get_spectrum(self,obj):
        results = obj.spectrum.filter(exists=True)
        return SpectrumDownSerializer(results,many=True,read_only=True).data


    def get_catalogue(self,obj):
        results = obj.catalogue.filter(exists=True)
        return CatalogueDownSerializer(results,many=True,read_only=True).data

    def get_imaging(self,obj):
        results = obj.imaging.filter(exists=True)
        return ImagingDownSerializer(results,many=True,read_only=True).data

        
    def __init__(self, *args, **kwargs):
        super(LensDownSerializerAll, self).__init__(*args, **kwargs)

        fields_to_remove = self.context.get('fields_to_remove')
        for field in fields_to_remove:
            self.fields.pop(field)

        lens_fields = self.context.get('lens_fields')
        if lens_fields is not None:
            allowed = set(lens_fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


        
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        #site = Site.objects.get_current()
        #mugshot_url = 'https://' + site.domain + ret['mugshot']
        #ret['mugshot'] = mugshot_url
        
        if 'papers' not in self.context['fields_to_remove']:
            flags = instance.papers(manager='objects').all().annotate(discovery=F('paperlensconnection__discovery'),
                                                                      model=F('paperlensconnection__model'),
                                                                      classification=F('paperlensconnection__classification'),
                                                                      #redshift=F('paperlensconnection__redshift')
                                                                      ).values("cite_as","discovery","model","classification")
            flag_dict = {}
            for flag in flags:
                cite_as = flag.pop('cite_as')
                flag_dict[cite_as] = flag

            for paper in ret["papers"]:
                paper["flags"] = flag_dict[paper['cite_as']]

        return ret

    
