from django.db.models import F
from lenses.models import Users, SledGroup, Lenses, DataBase, Imaging, Spectrum, Catalogue, Paper
from rest_framework import serializers, fields
from rest_framework.validators import UniqueValidator
import ads
from itertools import chain
       
### Users autocomplete
################################################################################
class UsersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Users
        fields = ('id','username','first_name','last_name','email')


        
### Groups autocomplete
################################################################################
class GroupsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SledGroup
        fields = ('id','name')


        
### Uploading data
################################################################################
class BaseDataFileUploadListSerializer(serializers.ListSerializer):
    def validate(self,attrs):
        ### Check that no two files are the same
        duplicate_files = []
        if attrs[0].get('image'):
            for i in range(0,len(attrs)-1):
                lens1 = attrs[i]
                file1 = lens1.get('image').name
                size1 = lens1.get('image').size

                for j in range(i+1,len(attrs)):
                    lens2 = attrs[j]
                    file2 = lens2.get('image').name
                    size2 = lens1.get('image').size

                    if file1 == file2 and size1 == size2:
                        duplicate_files.append(file1)

            if len(duplicate_files) > 0:
                raise serializers.ValidationError('More than one files have the same name and size which could indicate duplicates!')

        ### Check that there is at least one matching lens per datum
        print(attrs)
        for i in range(0,len(attrs)):
            ra = attrs[i].get('ra')
            dec = attrs[i].get('dec')
            user = attrs[i].get('owner')
            print(user, user)
            mybool = Lenses.proximate.get_DB_neighbours_anywhere_user_specific(ra,dec,user=attrs[i].get('owner'))
            print(mybool)
            if not mybool:
                raise serializers.ValidationError('The given RA,dec = (%f,%f) do not correspond to any public lens in the database!' % (ra,dec))

        return attrs


class ImagingDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=7,decimal_places=4)
    dec = serializers.DecimalField(max_digits=7,decimal_places=4)

    class Meta():
        model = Imaging
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = BaseDataFileUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Imaging(**validated_data)

    
class SpectrumDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=7,decimal_places=4)
    dec = serializers.DecimalField(max_digits=7,decimal_places=4)

    class Meta():
        model = Spectrum
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = BaseDataFileUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Spectrum(**validated_data)


class CatalogueDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=7,decimal_places=4)
    dec = serializers.DecimalField(max_digits=7,decimal_places=4)
    mag = serializers.DecimalField(max_digits=10, decimal_places=3, allow_null=True)


    class Meta():
        model = Catalogue
        exclude = ['lens','created_at','modified_at']
        #extra_kwargs = {'mag': {'allow_null': True}, 'Dmag': {'allow_null': True}} 
        #list_serializer_class = BaseDataFileUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Catalogue(**validated_data)

    
    
### Uploading lenses
################################################################################
class LensesUploadListSerializer(serializers.ListSerializer):

    def validate(self,attrs):
        print('validating the lens')
        ### Check proximity here
        check_radius = 16 # arcsec
        proximal_lenses = []
        for i in range(0,len(attrs)-1):
            lens1 = attrs[i]
            ra1 = lens1.get('ra')
            dec1 = lens1.get('dec')

            for j in range(i+1,len(attrs)):
                lens2 = attrs[j]
                ra2 = lens2.get('ra')
                dec2 = lens2.get('dec')

                if Lenses.distance_on_sky(ra1,dec1,ra2,dec2) < check_radius:
                    proximal_lenses.append(j)

        if len(proximal_lenses) > 0:
            message = 'Some lenses are too close to each other. This probably indicates a possible duplicate and submission through the API is not allowed.'
            raise serializers.ValidationError(message)

        ### Check that no two files are the same
        duplicate_files = []
        for i in range(0,len(attrs)-1):
            lens1 = attrs[i]
            file1 = lens1.get('mugshot').name
            size1 = lens1.get('mugshot').size

            for j in range(i+1,len(attrs)):
                lens2 = attrs[j]
                file2 = lens2.get('mugshot').name
                size2 = lens1.get('mugshot').size

                if file1 == file2 and size1 == size2:
                    duplicate_files.append(file1)
                    
        if len(duplicate_files) > 0:
            raise serializers.ValidationError('More than one files have the same name and size which could indicate duplicates!')

        return attrs


class LensesUploadSerializer(serializers.ModelSerializer):
    #z_lens = serializers.DecimalField(allow_null=True)
    LensTypeChoices = (
        ('GALAXY','Galaxy'),
        ('SPIRAL','Spiral galaxy'),
        ('GALAXY PAIR','Galaxy pair'),
        ('GROUP','Group of galaxies'),
        ('CLUSTER','Galaxy cluster'),
        ('CLUSTER MEMBER','Galaxy cluster member'),
        ('QUASAR','Quasar')
    )
    lens_type = fields.MultipleChoiceField(choices=LensTypeChoices, required=False)
    
    SourceTypeChoices = (
        ('GALAXY','Galaxy'),
        ('QUASAR','Quasar'),
        ('DLA','DLA'),
        ('PDLA','PDLA'),
        ('RADIO-LOUD','Radio-loud'),
        ('BAL QUASAR','BAL Quasar'),
        ('ULIRG','ULIRG'),
        ('BL Lac','BL Lac'),
        ('LOBAL QUASAR','LoBAL Quasar'),
        ('FELOBAL QUASAR','FeLoBAL Quasar'),
        ('EXTREME RED OBJECT','Extreme Red Object'),
        ('RED QUASAR','Red Quasar'),
        ('GW','Gravitational Wave'),
        ('FRB','Fast Radio Burst'),
        ('GRB','Gamma Ray Burst'),
        ('SN','Supernova')
    )
    source_type = fields.MultipleChoiceField(choices=SourceTypeChoices, required=False)

    ImageConfChoices = (
        ('LONG-AXIS CUSP','Long-axis Cusp'),
        ('SHORT-AXIS CUSP','Short-axis Cusp'),
        ('NAKED CUSP','Naked Cusp'),
        ('CUSP','Cusp'),
        ('CENTRAL IMAGE','Central Image'),
        ('FOLD','Fold'),
        ('CROSS','Cross'),
        ('DOUBLE','Double'),
        ('QUAD','Quad'),
        ('RING','Ring'),
        ('ARC','Arc')
    )

    image_conf = fields.MultipleChoiceField(choices=ImageConfChoices, required=False)

    class Meta:
        model = Lenses
        exclude = ['owner','created_at','modified_at']
        list_serializer_class = LensesUploadListSerializer
        
    def create(self,validated_data):
        return Lenses(**validated_data)


### Uploading papers
################################################################################
class PaperUploadListSerializer(serializers.ListSerializer):
    def validate(self,papers):
        
        bibcodes = [paper['bibcode'] for paper in papers]

        ## Check for duplicate bibcodes within the uploaded data
        seen = set()
        dupl = []
        for code in bibcodes:
            if code not in seen:
                seen.add(code)
            else:
                dupl.append(code)
        if len(dupl) != 0:
            raise serializers.ValidationError('There are duplicate bibcodes: '+','.join(dupl))


        ## Check ADS if bibcodes are valid and fetch data that will be added to validated_data
        ## Check only at the end in order not to waste calls to the ADS API.
        ads.config.token = 'vL9nHFH4ozMNFtds3lwRnvmXOW8W2xdJIznHa4TO'
        r = ads.RateLimits('SearchQuery')
        q = ads.SearchQuery(bibcode="2022MNRAS.516.1347V") # random bibcode to test the remaining queries
        q.execute()
        print(r.limits['remaining'])
        if r.limits['remaining'] == 0:
            raise serializers.ValidationError('Daily limit of contacting the ADS API has been reached. Try again in 24 hours!')

        not_in_ads = []
        in_ads = []
        for code in bibcodes:
            articles = list(ads.SearchQuery(bibcode=code,fl=['recid','title','year','first_author','author']))
            if len(articles) == 0:
                not_in_ads.append(code)
            else:
                in_ads.append(articles[0])
        if len(not_in_ads) != 0:
            if len(not_in_ads) == 1:
                raise serializers.ValidationError('This bibcode does not exist in ADS: ' + not_in_ads[0])
            else:
                raise serializers.ValidationError('These bibcodes do not exist in ADS: ' + ','.join(not_in_ads))

        ads_ids = []
        for i,paper in enumerate(papers):
            ads_ids.append(in_ads[i].recid)
            paper.ads_id = in_ads[i].recid
            paper.title = in_ads[i].title[0]
            paper.year = in_ads[i].year
            paper.first_author = in_ads[i].first_author
            if len(in_ads[i].author) > 2:
                paper.cite_as = paper.first_author + ' et al. (' + paper.year + ')'
            else:
                paper.cite_as = ' and '.join(in_ads[i].author) + ' (' + paper.year + ')'
        #print(ads_ids)
        
        ## Check that ads_id do not exist already in the database
        existing = Paper.objects.filter(ads_id__in=ads_ids).values('bibcode','cite_as')
        if len(existing) != 0:
            labels = []
            for q in existing:
                labels.append( q['cite_as']+' ('+q['bibcode']+')' )
            raise serializers.ValidationError('These bibcodes already exist: '+'\n'.join(labels))


    
        ## Loop over papers and check for proximity.
        ## If not all lenses exist, return paper and RA,DEC that do not exist.
        lenses_per_paper = []
        for paper in papers:
            N_lenses = len(paper['lenses']) 
            ras  = []
            decs = []
            for lens in paper['lenses']:
                ras.append(lens['ra'])
                decs.append(lens['dec'])
            user = self.context['request'].user
            indices,neis = Lenses.proximate.get_DB_neighbours_anywhere_many_user_specific(ras,decs,user,radius=3) # This call includes PRI lenses visible to the user
            
            if len(indices) != N_lenses:
                setA = set(indices)
                setB = set(range(0,N_lenses))
                missing = setB - setA
                labels = []
                for k in missing:
                    labels.append( '(' + str(ras[k]) + ',' + str(decs[k]) + ')' )
                raise serializers.ValidationError('These RA,DEC do NOT correspond to any lens in the database:\n '+'\n'.join(labels))
            else:
                lenses = list( neis )
                if len(lenses) != N_lenses:
                    # This means that one (or more) lens(es) from dum_lenses matched to more than one lens from the DB
                    # It is a duplicate problem...
                    labels = []
                    for k in range(0,len(neis)):
                        if len(neis[k]) > 1:
                            labels.append( '(' + str(ras[k]) + ',' + str(decs[k]) + ')' )
                    raise serializers.ValidationError('Contact the admins: potential duplicates in the database for: ' + '\n'.join(labels))
                else:
                    # Queryset evaluation happens here
                    dum = []
                    for q in neis:
                        dum.extend( list(q) )
                    lenses_per_paper.append( dum )


        
        ## Loop over papers and check for discovery
        lenses_with_discovery = []
        for i,paper in enumerate(papers):
            for j,lens in enumerate(lenses_per_paper[i]):
                if papers[i]["lenses"][j]["discovery"]:
                    lenses_with_discovery.append(lenses_per_paper[i][j])

        ## We don't want to claim discovery papers ourselves, so the 'if' statement below is not needed because there will be no unique discovery paper.
        #if len(lenses_with_discovery) != 0:
        #    ## Check for duplicate discovery papers within the uploaded data
        #    seen = set()
        #    dupl = []
        #    for lens in lenses_with_discovery:
        #        if lens.name not in seen:
        #            seen.add(lens.name)
        #        else:
        #            dupl.append(lens.name)
        #    if len(dupl) != 0:
        #        raise serializers.ValidationError('There are duplicate discovery papers in the upload: '+','.join(dupl))
        #            
        #    ## Check database for existing discovery papers (only for those lenses that have been specified here as discovery)
        #    ## Object access in the call below is already delegated by proximate.get_DB_neighbours_many
        #    qset = Lenses.objects.filter(id__in=[lens.id for lens in lenses_with_discovery],paperlensconnection__discovery=True).annotate(paper=F('papers__cite_as'))
        #    if len(qset) > 0:
        #        labels = []
        #        for lens in qset:
        #            labels.append(lens.name + ' - ' + lens.paper)
        #        raise serializers.ValidationError('Discovery papers already exist for: ' + '\n'.join(labels))

        flags_per_paper = []
        for paper in papers:
            flags_and_lenses = []
            for lens in paper['lenses']:
                flags_and_lenses.append(
                    {
                        "discovery": lens["discovery"],
                        "classification": lens["classification"],
                        "redshift": lens["redshift"],
                        "model": lens["model"]
                    }
                )
            flags_per_paper.append(flags_and_lenses)



        new_papers = []
        for i,paper in enumerate(papers):
            new_paper = {
                "ads_id": paper.ads_id,
                "bibcode": paper["bibcode"],
                "title": paper.title,
                "year": paper.year,
                "first_author": paper.first_author,
                "cite_as": paper.cite_as
            }
            new_papers.append(new_paper)



        ## Final validated data structure
        validated_data = {
            "papers": new_papers,
            "lenses_per_paper": lenses_per_paper,
            "flags_per_paper": flags_per_paper
        }

        #raise serializers.ValidationError('DUM error raised. Stop')
        return validated_data



class PaperLensSerializer(serializers.Serializer):
    ra = serializers.FloatField(min_value=0,max_value=360)
    dec = serializers.FloatField(min_value=-90,max_value=90)
    discovery = serializers.BooleanField()
    classification = serializers.BooleanField()
    model = serializers.BooleanField()
    redshift = serializers.BooleanField()

    
class PaperUploadSerializer(serializers.Serializer):
    bibcode = serializers.CharField(max_length=19)
    lenses = serializers.ListField(
        child=PaperLensSerializer()
    )
    
    class Meta():
        list_serializer_class = PaperUploadListSerializer
        
    def create(self,validated_data):
        return Papers(**validated_data)

    def validate(self,data):
        ### Check proximity of given lenses with each other
        check_radius = 16 # arcsec
        proximal_lenses = []
        for i in range(0,len(data['lenses'])-1):
            ra1 = data['lenses'][i]['ra']
            dec1 = data['lenses'][i]['dec']

            for j in range(i+1,len(data['lenses'])):
                ra2 = data['lenses'][j]['ra']
                dec2 = data['lenses'][j]['dec']

                if Lenses.distance_on_sky(ra1,dec1,ra2,dec2) < check_radius:
                    proximal_lenses.append(j)

        if len(proximal_lenses) > 0:
            message = 'Some lenses are too close to each other. This probably indicates a possible duplicate and submission is not allowed.'
            raise serializers.ValidationError(message)

        return data
