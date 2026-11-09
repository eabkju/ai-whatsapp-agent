import time
from collections import deque

class ContactJob:
    def __init__(self, name, bounds, is_group=False, last_msg=""):
        self.name = name
        self.bounds = bounds
        self.is_group = is_group
        self.last_msg = last_msg
        self.enqueued_at = time.time()

class QueueManager:
    def __init__(self, cooldown_seconds=25):
        self.cooldown_seconds = cooldown_seconds
        self.queue = deque()  # ContactJob objects
        self.enqueued_names = set()
        self.last_reply_time = {}  # {contact_name: timestamp}

    def sync_incoming_contacts(self, discovered_chats):
        """
        Discovers unread chats from WhatsApp home screen.
        Maintains FIFO order. If a contact already replied or in queue sends another message,
        it is placed at the tail of the queue.
        """
        current_time = time.time()
        for chat in discovered_chats:
            name = chat["name"]
            
            # If already in the active waiting queue, update latest bounds/msg
            if name in self.enqueued_names:
                for job in self.queue:
                    if job.name == name:
                        job.bounds = chat["bounds"]
                        job.last_msg = chat.get("last_msg", "")
                        break
                continue

            # Check if contact is on cooldown
            time_since_reply = current_time - self.last_reply_time.get(name, 0)
            if time_since_reply < self.cooldown_seconds:
                # Still within 25s cooldown window, skip for now
                continue

            # Add to tail of queue
            job = ContactJob(
                name=name,
                bounds=chat["bounds"],
                is_group=chat.get("is_group", False),
                last_msg=chat.get("last_msg", "")
            )
            self.queue.append(job)
            self.enqueued_names.add(name)

    def get_next_job(self):
        """
        Retrieves the next eligible contact job according to FIFO fairness.
        """
        if not self.queue:
            return None

        current_time = time.time()
        # Look from the front
        attempts = len(self.queue)
        for _ in range(attempts):
            job = self.queue.popleft()
            time_since_reply = current_time - self.last_reply_time.get(job.name, 0)
            if time_since_reply >= self.cooldown_seconds:
                self.enqueued_names.discard(job.name)
                return job
            else:
                # If on cooldown, move to tail
                self.queue.append(job)

        return None

    def requeue_contact(self, name, bounds, last_msg=""):
        """
        Explicitly appends a contact to the back of the queue (e.g. sent another message).
        """
        if name in self.enqueued_names:
            # Remove from current position and append to tail
            new_queue = deque()
            matched_job = None
            for job in self.queue:
                if job.name == name:
                    matched_job = job
                else:
                    new_queue.append(job)
            if matched_job:
                matched_job.bounds = bounds
                matched_job.last_msg = last_msg
                new_queue.append(matched_job)
            self.queue = new_queue
        else:
            job = ContactJob(name=name, bounds=bounds, last_msg=last_msg)
            self.queue.append(job)
            self.enqueued_names.add(name)

    def record_reply_sent(self, name):
        """Updates timestamp of last reply to enforce 25-second cooldown."""
        self.last_reply_time[name] = time.time()
        self.enqueued_names.discard(name)

    def is_on_cooldown(self, name):
        return (time.time() - self.last_reply_time.get(name, 0)) < self.cooldown_seconds

    def remaining_cooldown(self, name):
        elapsed = time.time() - self.last_reply_time.get(name, 0)
        return max(0, self.cooldown_seconds - elapsed)

    def queue_length(self):
        return len(self.queue)
