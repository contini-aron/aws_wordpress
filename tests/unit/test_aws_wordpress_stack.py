import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_wordpress.aws_wordpress_stack import AwsWordpressStack


# example tests. To run these tests, uncomment this file along with the example
# resource in aws_wordpress/aws_wordpress_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsWordpressStack(app, "aws-wordpress")
    template = assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
