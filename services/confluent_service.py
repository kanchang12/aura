from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic
import json
from config import Config
import socket

class ConfluentService:
    """Confluent Kafka service for real-time event streaming"""

    def __init__(self):
        self.config = {
            'bootstrap.servers': Config.CONFLUENT_BOOTSTRAP_SERVERS,
            'sasl.mechanisms': 'PLAIN',
            'security.protocol': 'SASL_SSL',
            'sasl.username': Config.CONFLUENT_API_KEY,
            'sasl.password': Config.CONFLUENT_API_SECRET,
        }

        # Producer for sending events
        self.producer = Producer({
            **self.config,
            'client.id': socket.gethostname()
        })

        # Topics
        self.TOPIC_TASKS = 'user-tasks'
        self.TOPIC_SESSIONS = 'user-sessions'
        self.TOPIC_NOTIFICATIONS = 'task-notifications'

        # Create topics if they don't exist
        self._create_topics()

    def _create_topics(self):
        """Create Kafka topics if they don't exist"""
        try:
            admin_client = AdminClient(self.config)

            topics = [
                NewTopic(self.TOPIC_TASKS, num_partitions=3, replication_factor=3),
                NewTopic(self.TOPIC_SESSIONS, num_partitions=3, replication_factor=3),
                NewTopic(self.TOPIC_NOTIFICATIONS, num_partitions=3, replication_factor=3)
            ]

            # Create topics
            futures = admin_client.create_topics(topics)

            for topic, future in futures.items():
                try:
                    future.result()
                    print(f"Topic {topic} created")
                except Exception as e:
                    if 'TopicExistsError' not in str(e):
                        print(f"Failed to create topic {topic}: {e}")

        except Exception as e:
            print(f"Error creating topics: {e}")

    def _delivery_report(self, err, msg):
        """Kafka delivery callback"""
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def publish_task_event(self, user_id, task_data):
        """
        Publish a task creation/update event

        Args:
            user_id: User ID
            task_data: Task information (dict)
        """
        try:
            event = {
                'user_id': user_id,
                'task': task_data,
                'timestamp': task_data.get('created_at'),
                'event_type': 'task_created'
            }

            self.producer.produce(
                self.TOPIC_TASKS,
                key=str(user_id),
                value=json.dumps(event),
                callback=self._delivery_report
            )

            self.producer.flush()

        except Exception as e:
            print(f"Error publishing task event: {e}")

    def publish_session_event(self, user_id, session_data):
        """
        Publish a session start/end event

        Args:
            user_id: User ID
            session_data: Session information (dict)
        """
        try:
            event = {
                'user_id': user_id,
                'session': session_data,
                'timestamp': session_data.get('started_at'),
                'event_type': session_data.get('event_type', 'session_started')
            }

            self.producer.produce(
                self.TOPIC_SESSIONS,
                key=str(user_id),
                value=json.dumps(event),
                callback=self._delivery_report
            )

            self.producer.flush()

        except Exception as e:
            print(f"Error publishing session event: {e}")

    def publish_notification_event(self, user_id, notification_data):
        """
        Publish a notification event for task reminders

        Args:
            user_id: User ID
            notification_data: Notification information (dict)
        """
        try:
            event = {
                'user_id': user_id,
                'notification': notification_data,
                'timestamp': notification_data.get('timestamp'),
                'event_type': 'notification_triggered'
            }

            self.producer.produce(
                self.TOPIC_NOTIFICATIONS,
                key=str(user_id),
                value=json.dumps(event),
                callback=self._delivery_report
            )

            self.producer.flush()

        except Exception as e:
            print(f"Error publishing notification event: {e}")

    def create_consumer(self, topic, group_id):
        """
        Create a Kafka consumer for a specific topic

        Args:
            topic: Topic to subscribe to
            group_id: Consumer group ID

        Returns:
            Consumer: Kafka consumer instance
        """
        try:
            consumer = Consumer({
                **self.config,
                'group.id': group_id,
                'auto.offset.reset': 'earliest'
            })

            consumer.subscribe([topic])
            return consumer

        except Exception as e:
            print(f"Error creating consumer: {e}")
            return None

    def process_task_reminders(self):
        """
        Background process to consume task events and trigger reminders
        This would typically run as a separate service/worker
        """
        consumer = self.create_consumer(self.TOPIC_TASKS, 'task-reminder-group')

        if not consumer:
            return

        try:
            while True:
                msg = consumer.poll(1.0)

                if msg is None:
                    continue
                if msg.error():
                    print(f"Consumer error: {msg.error()}")
                    continue

                # Process the message
                event = json.loads(msg.value().decode('utf-8'))
                task = event.get('task')
                user_id = event.get('user_id')

                # Logic to schedule notifications based on task
                if task and task.get('schedule_time'):
                    notification = {
                        'user_id': user_id,
                        'task_id': task.get('id'),
                        'message': f"Reminder: {task.get('description')}",
                        'timestamp': task.get('schedule_time'),
                        'type': 'task_reminder'
                    }

                    self.publish_notification_event(user_id, notification)

        except KeyboardInterrupt:
            pass
        finally:
            consumer.close()
