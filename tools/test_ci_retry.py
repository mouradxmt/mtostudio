import unittest
from ci.retry import retry

class BuildRetryTest(unittest.TestCase):
    def test_temporary_download_error_retries_identical_command(self):
        calls=[];delays=[]
        def invoke(command):
            calls.append(command[:]); return (1,'HTTP Error 504') if len(calls)==1 else (0,'verified')
        self.assertEqual(retry(['build','--locked'],invoke,delays.append),0)
        self.assertEqual(calls,[['build','--locked'],['build','--locked']]);self.assertEqual(delays,[10])
    def test_license_failure_is_never_retried_or_approved(self):
        calls=[]
        def invoke(command):calls.append(command);return (1,'License/dependency inputs differ from reviewed inventory')
        self.assertEqual(retry(['build'],invoke,lambda _:self.fail('Retried a license gate')),1)
        self.assertEqual(len(calls),1)
    def test_repeated_outage_stops_after_three_attempts(self):
        calls=[]
        def invoke(command):calls.append(command);return (7,'HTTP Error 503')
        self.assertEqual(retry(['build'],invoke,lambda _:None),7);self.assertEqual(len(calls),3)

if __name__ == '__main__':unittest.main()
