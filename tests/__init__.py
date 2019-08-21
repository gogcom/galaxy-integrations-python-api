import json


def create_message(request):
    return json.dumps(request).encode() + b"\n"


def get_messages(write_mock):
    messages = []
    for call_args in write_mock.call_args_list:
        data = call_args[0][0]
        for line in data.splitlines():
            message = json.loads(line)
            messages.append(message)
    return messages

