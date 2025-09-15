import unittest
from unittest.mock import MagicMock, patch
from app import email_service
import os
import datetime

class TestEmailService(unittest.TestCase):
    def setUp(self):
        self.mock_service = MagicMock()
        os.environ['SENDER_NAME'] = 'Test Sender'
        os.environ['MIN_DAYS'] = '2'
        os.environ['MAX_DAYS'] = '30'
        os.environ['BATCH_SIZE'] = '5'
        self.current_time = datetime.datetime(2025, 9, 15)
        self.test_email = 'me@example.com'

    def create_mock_thread(self, thread_id, message_count, base_date, subject_prefix="Interest in"):
        messages = []
        for i in range(message_count):
            date = (base_date + datetime.timedelta(days=i)).timestamp() * 1000
            subject = f"{subject_prefix} Product" if i == 0 else f"Re: {subject_prefix} Product"
            messages.append({
                'id': f'm{thread_id}_{i}',
                'threadId': f't{thread_id}',
                'payload': {'headers': [
                    {'name': 'Subject', 'value': subject},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'From', 'value': self.test_email}
                ]},
                'internalDate': str(int(date)),
                'snippet': f'Message {i} content'
            })
        return {'messages': messages}

    @patch('app.report_service.generate_followup_report')
    def test_get_threads_multiple_batches(self, mock_report):
        # Patch datetime inside email_service
        with patch('app.email_service.datetime') as mock_datetime:
            mock_datetime.datetime.utcnow.return_value = self.current_time
            mock_datetime.datetime.fromtimestamp = datetime.datetime.fromtimestamp
            mock_datetime.timedelta = datetime.timedelta
            self.mock_service.users().getProfile().execute.return_value = {'emailAddress': self.test_email}
            base_date = self.current_time - datetime.timedelta(days=7)
            self.mock_service.users().messages().list().execute.side_effect = [
                {'messages': [{'threadId': f't{i}'} for i in range(1, 6)], 'nextPageToken': 'token1'},
                {'messages': [{'threadId': f't{i}'} for i in range(6, 11)], 'nextPageToken': 'token2'},
                {'messages': [{'threadId': f't{i}'} for i in range(11, 16)], 'nextPageToken': None}
            ]
            thread_responses = {}
            for i in range(1, 16):
                thread = self.create_mock_thread(i, i % 3 + 1, base_date)
                # Ensure all messages are from user and first subject starts with 'Interest in'
                for msg in thread['messages']:
                    msg['payload']['headers'].append({'name': 'From', 'value': self.test_email})
                thread['messages'][0]['payload']['headers'][0]['value'] = 'Interest in Product'
                thread_responses[f't{i}'] = thread
            def mock_get_thread(userId, id):
                mock = MagicMock()
                mock.execute.return_value = thread_responses[id]
                return mock
            self.mock_service.users().threads().get.side_effect = mock_get_thread
            threads = email_service.get_threads_to_follow_up(self.mock_service)
            self.assertTrue(len(threads) > 0)
            self.assertEqual(self.mock_service.users().messages().list().execute.call_count, 3)
            mock_report.assert_called_once()

    @patch('app.report_service.generate_followup_report')
    def test_get_threads_with_varying_lengths(self, mock_report):
        with patch('app.email_service.datetime') as mock_datetime:
            mock_datetime.datetime.utcnow.return_value = self.current_time
            mock_datetime.datetime.fromtimestamp = datetime.datetime.fromtimestamp
            mock_datetime.timedelta = datetime.timedelta
            self.mock_service.users().getProfile().execute.return_value = {'emailAddress': self.test_email}
            thread_lengths = [1, 3, 5]
            base_date = self.current_time - datetime.timedelta(days=5)
            self.mock_service.users().messages().list().execute.return_value = {
                'messages': [{'threadId': f't{i}'} for i in range(len(thread_lengths))]
            }
            thread_responses = {}
            for i, length in enumerate(thread_lengths):
                thread = self.create_mock_thread(i, length, base_date)
                # Ensure all messages are from user and first subject starts with 'Interest in'
                for msg in thread['messages']:
                    msg['payload']['headers'].append({'name': 'From', 'value': self.test_email})
                thread['messages'][0]['payload']['headers'][0]['value'] = 'Interest in Product'
                thread_responses[f't{i}'] = thread
            def mock_get_thread(userId, id):
                mock = MagicMock()
                mock.execute.return_value = thread_responses[id]
                return mock
            self.mock_service.users().threads().get.side_effect = mock_get_thread
            threads = email_service.get_threads_to_follow_up(self.mock_service)
            self.assertEqual(len(threads), 2)
            for i, thread in enumerate(threads):
                self.assertEqual(thread['followup_count'], thread_lengths[i] - 1)

    def test_count_followups_with_varying_subjects(self):
        msgs = [
            {'payload': {'headers': [{'name': 'Subject', 'value': 'Interest in Product'}]}},
            {'payload': {'headers': [{'name': 'Subject', 'value': 'Re: Interest in Product'}]}},
            {'payload': {'headers': [{'name': 'Subject', 'value': 'Follow up on Product'}]}},
            {'payload': {'headers': [{'name': 'Subject', 'value': 'Re: Follow up on Product'}]}},
            {'payload': {'headers': [{'name': 'Subject', 'value': 'Quick follow up'}]}}
        ]
        self.assertEqual(email_service.count_followups(msgs), 4)

    def test_edge_cases(self):
        empty_thread = {'messages': []}
        self.assertEqual(email_service.count_followups(empty_thread['messages']), 0)
        no_headers_msg = {'payload': {'headers': []}}
        self.assertEqual(email_service.get_header(no_headers_msg, 'Subject'), '')
        malformed_msg = {'payload': {}}
        self.assertEqual(email_service.get_header(malformed_msg, 'Subject'), '')
        completely_malformed_msg = {}
        self.assertEqual(email_service.get_header(completely_malformed_msg, 'Subject'), '')
        self.assertFalse(email_service.is_from_user(malformed_msg, self.test_email))
        self.assertFalse(email_service.is_from_user(completely_malformed_msg, self.test_email))

if __name__ == "__main__":
    unittest.main()
