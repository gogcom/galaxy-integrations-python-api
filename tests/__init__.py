import json


def create_message(request):
    return json.dumps(request).encode() + b"\n"


def get_messages(write_mock):
    messages = []
    print("call_args_list", write_mock.call_args_list)
    for call_args in write_mock.call_args_list:
        print("call_args", call_args)
        data = call_args[0][0]
        print("data", data)
        for line in data.splitlines():
            message = json.loads(line)
            messages.append(message)
    return messages

