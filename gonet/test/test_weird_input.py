import io
from django.test import TransactionTestCase
from django.test import Client
from django import urls
from pkg_resources import resource_filename as pkg_file
from ..models import GOnetSubmission
import pandas as pd
from . import job_req

c = Client()
class WeirdInputTestCase(TransactionTestCase):
    def test_resolution_accidental_space(self):
        
        input_lines = '\n'.join(["BLK", "GAS6", "CD1C ", "SEPT4"])
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        self.assertEqual(resp.status_code, 200)
        sn = GOnetSubmission.objects.latest('submit_time')
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        self.assertEqual(res.loc['CD1C', 'Uniprot_ID'], 'P29017')

    def test_empty_submission(self):
        input_lines = ''
        req = dict(job_req, **{'paste_data':input_lines})
        resp = c.get(urls.reverse('GOnet-submit-form'))
        self.assertEqual(resp.status_code, 200)
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'File with gene list should be uploaded')

    def test_custom_annot_no_input(self):
        input_lines = open(pkg_file(__name__, 'data/genelist1.lst'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Custom GO terms option specified')


    def test_wrong_separator(self):
        input_lines = open(pkg_file(__name__, 'data/genelist4.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'None of the genes submitted')
        self.assertContains(resp, 'IGLV3-27        1.204029972')

    def test_wrong_species(self):
        input_lines = open(pkg_file(__name__, 'data/genelist7.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol', 'organism':'human'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'None of the genes submitted')

    def test_maximum_entries_graph_output(self):
        
        input_lines = open(pkg_file(__name__, 'data/genelist8.tsv'), 'r').read().split('\n')
        input_str = '\n'.join(input_lines[:5000])
        req = dict(job_req, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'incompatible with output type &quot;Graph&quot')

    def test_one_line_entries(self):
        input_str = 'TAF13, AFP, ELMO2, PITX3, FSHB, KCNJ6'
        req = dict(job_req, **{'paste_data':input_str, 'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Multiple separators detected')

    def test_too_many_entries(self):
        input_str = '\n'.join(['ABC']*21000)
        req = dict(job_req, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Maximum number of entries is 20000.')

    def test_multiword_header_whitespace_delim(self):
        input_str = '\n'.join(['Humanized 9035 Mouse Gene Symbol', 'SPINK1', 'EPCAM'])
        req = dict(job_req, **{'paste_data':input_str, 'csv_separator':'\s+',
                               'analysis_type':'annot', 'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Multiple separators detected')

    def test_multiword_line_whitespace_delim(self):
        input_str = '\n'.join(['SPINK1', 'Humanized 9035 Mouse Gene Symbol', 'EPCAM'])
        req = dict(job_req, **{'paste_data':input_str, 'csv_separator':'\s+',
                               'analysis_type':'annot', 'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        gn = sn.parsed_data
        self.assertIn('Humanized', list(gn.submit_name))

    def test_numbers_only_input(self):
        input_str = '5443\r\n5743\r\n627\r\n6323\r\n7124'
        req = dict(job_req, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic', 'organism':'human'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'None of the genes submitted')
        
    def test_integer_contrast_value(self):
        input_str = '1700094D03Rik	73545\n'
        req = dict(job_req, **{'paste_data':input_str, 'organism':'mouse'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)

    def test_integer_contrast_value_any_whitespace(self):
        input_str = '1700094D03Rik	73545\nABC1	120\n'
        req = dict(job_req, **{'paste_data':input_str, 'organism':'mouse',
                               'csv_separator':'\s+'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        gn = sn.parsed_data
        self.assertEqual(gn.shape[0], 2)

    def test_upload_binary(self):
        fl = open(pkg_file(__name__, 'data/genelist10.csv'), 'rb')
        req = dict(job_req, **{'uploaded_file':fl, 'organism':'human'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Error occured while validating')

    def test_alt_namebraces(self):
        input_str = '\n'.join(['PYGM 2', 'profilin 2(PFN2) 2', 'KPNB1 2'])
        req = dict(job_req, **{'paste_data':input_str, 'csv_separator':'\s+',
                               'analysis_type':'annot', 'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        row = sn.parsed_data[sn.parsed_data.submit_name=='profilin'].iloc[0]
        self.assertTrue(pd.isna(row['val']))
        
    def test_upload_empty_file(self):
        fl = open(pkg_file(__name__, 'data/genelist13.txt'), 'rb')
        req = dict(job_req, **{'uploaded_file':fl})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Uploaded file is empty')
        
