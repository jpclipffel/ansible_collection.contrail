#!/bin/bash

cd $(dirname ${0})
ansible-galaxy collection build --force
ansible-galaxy collection install jpclipffel-contrail-1.0.0.tar.gz
