from behave import *


@given('Container is running')
def step_impl(context):
    assert context.release_monitor.status == 'created'


@then('Check container logs for "{count}" received elements from "{registry}"')
def step_impl(context, count, registry):
    event_count = 0
    for e in context.release_monitor.logs(stream=True):
        if "Processing package from {registry}".format(registry=registry) in e.decode('utf-8'):
            event_count = event_count + 1

        if event_count >= int(count):
            break
