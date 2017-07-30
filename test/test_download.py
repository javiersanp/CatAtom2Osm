import unittest
import mock
import random

import main
from download import ProgressBar, get_response, wget, chunk_size


class TestProgressBar(unittest.TestCase):

    def test_init(self):
        p = ProgressBar(1000)
        self.assertEquals(p.total, 1000)
        self.assertEquals(p.progress, 0)

    @mock.patch('download.sys')
    def test_update(self, mock_sys):
        pb = ProgressBar(1000)
        progress = random.randint(0, 9)
        pb.update(100 * progress)
        self.assertEquals(pb.progress, 100 * progress)
        self.assertTrue(mock_sys.stdout.write.called)
        output = mock_sys.stdout.write.call_args_list[0][0][0]
        self.assertEquals(output.count('#'), int(pb.bar_len * progress / 10.0))
        self.assertEquals(output.count('-'), int(pb.bar_len * (10-progress) / 10.0))

    @mock.patch('download.sys')
    def test_update100(self, mock_sys):
        pb = ProgressBar(1000)
        pb.update(1100)
        self.assertEquals(pb.progress, 1000)
        self.assertTrue(mock_sys.stdout.write.called)
        output = mock_sys.stdout.write.call_args_list[0][0][0]
        self.assertEquals(output.count('#'), pb.bar_len)
        self.assertEquals(output.count('-'), 0)
    
    @mock.patch('download.sys')
    def test_update0(self, mock_sys):
        pb = ProgressBar(0)
        progress = random.randint(0, 99999)
        pb.update(progress)
        self.assertTrue(mock_sys.stdout.write.called)
        output = mock_sys.stdout.write.call_args_list[0][0][0]
        self.assertEquals(output.split(': ')[1], '%.1fK\r' % (progress / 1024.0))


class TestGetResponse(unittest.TestCase):
    
    @mock.patch('download.requests')
    def test_get_response_ok(self, mock_requests):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_requests.codes.ok = 200
        mock_requests.get.return_value = mock_response
        r = get_response('foo', 'bar')
        self.assertEquals(r, mock_response)
        mock_requests.get.assert_called_once_with('foo', stream='bar', timeout=30)

    @mock.patch('download.requests')
    def test_get_response_bad(self, mock_requests):
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_requests.codes.ok = 200
        mock_requests.get.return_value = mock_response
        get_response('foo', 'bar')
        self.assertEquals(mock_requests.get.call_count, 3)
        mock_response.raise_for_status.assert_called_once_with()


class TestWget(unittest.TestCase):

    @mock.patch('download.get_response')
    @mock.patch('download.ProgressBar')
    @mock.patch('download.open')
    def test_wget(self, mock_open, mock_pb, mock_gr):
        mock_gr.return_value = mock.MagicMock()
        mock_gr.return_value.iter_content = range
        mock_gr.return_value.headers = {'Content-Length': '99999'}
        file_mock = mock.MagicMock()
        mock_open.return_value = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = file_mock
        wget('foo', 'bar')
        self.assertEquals(file_mock.write.call_count, chunk_size)
        mock_pb.assert_called_once_with(99999)
    
    @mock.patch('download.get_response')
    @mock.patch('download.ProgressBar')
    @mock.patch('download.open')
    def test_wget0(self, mock_open, mock_pb, mock_gr):
        mock_gr.return_value = mock.MagicMock()
        mock_gr.return_value.iter_content = range
        mock_gr.return_value.headers = {}
        file_mock = mock.MagicMock()
        mock_open.return_value = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = file_mock
        wget('foo', 'bar')
        self.assertEquals(file_mock.write.call_count, chunk_size)
        mock_pb.assert_called_with(0)

