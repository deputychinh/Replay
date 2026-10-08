#!/usr/bin/env python3
"""Relay on AWS.  cdk synth -c stage=staging|prod -c imageTag=<git sha> [-c appUrl=https://… -c alertEmail=…]"""

from aws_cdk import App

from relay_infra.app_builder import build

app = App()
build(app)
app.synth()
