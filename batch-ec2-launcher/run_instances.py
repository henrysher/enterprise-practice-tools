
base_ami_id = "ami-cb19c4a6" // Amazon Linux AMI
#base_ami_id = "ami-ea1ac687" // Windows 2016 AMI
base_key_pair_name = "launch_template"
csv_file = "instances_test.csv"

keywords = ["IP", "Public IP", "VPC", "Subnet", "Type", "OS", "EBS", "Security Group1", "Security Group2"]

import string
import csv
data = {}
tags = []

print "Reading CSV..."
with open(csv_file, 'rb') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    row_one = next(spamreader)
    for row in spamreader:
        data[row[0]] = {}
        for num in range(0, len(row)-1):
            data[row[0]][row_one[num]] = row[num]
            if row_one[num] not in keywords:
                tags.append(row_one[num])

tags = list(set(tags))
#print data


import sys, traceback
import boto3
client = boto3.client('ec2')

print "Launching instances..."
for instance in data.keys():

    print "\nChecking instance: %s..." % instance
    try:
        instance_check = client.describe_instances(
            Filters=[
                {   
                    'Name': 'tag:Name',
                    'Values': [
                        instance,
                    ]
                },
            ],
        )["Reservations"]
        if instance_check:
            count = 0
            for resv in instance_check:
                resp = resv["Instances"]
                for inode in resp:
                    print "Found existing instance: %s, %s" % (inode["InstanceId"], 
                                                               inode["State"]["Name"])
                    if inode["State"]["Name"] != "terminated":
                        count += 1
            if count:    
                continue
        else:
            print "No found..."
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print "...Failed"
        continue

    print 'Launching "%s"' % instance
    os = data[instance]["OS"]
    ebs_data = data[instance]["EBS"]

    sg1 = data[instance]["Security Group1"]
    sg2 = data[instance]["Security Group2"]
    try:
        sg1_id = client.describe_security_groups(
            Filters=[
                {
                    'Name': 'group-name',
                    'Values': [
                        sg1,
                    ]
                },
            ],
        )["SecurityGroups"][0]["GroupId"]
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print "...Failed"
        continue
    try:
        sg2_id = client.describe_security_groups(
            Filters=[
                {
                    'Name': 'group-name',
                    'Values': [
                        sg2,
                    ]
                },
            ],
        )["SecurityGroups"][0]["GroupId"]
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print "...Failed"
        continue

    block_device_mappings = []
    ebs_sizes = ebs_data.split("+")
    if "+" in ebs_data:
        for i in range(0, len(ebs_sizes)):
            if i == 0:
                if "Win" in os:
                    device_name = "/dev/sda1"
                    delete_on_termination = True
                else:
                    device_name = "/dev/xvda"
                    delete_on_termination = True
            else:
                device_name = "/dev/xvd" + string.ascii_lowercase[i]
                delete_on_termination = False
            
            block_device_mappings.append(
                {
                    'DeviceName': device_name,
                    'Ebs': {
                        'DeleteOnTermination': delete_on_termination,
                        'VolumeSize': int(ebs_sizes[i]),
                        'VolumeType': 'gp2'
                    },
                },
            )

    instance_tags = []
    for tag in tags:
        tag_key = tag
        tag_value = data[instance][tag]     
    
        instance_tags.append({
            'Key': tag_key,
            'Value': tag_value
        })
   
    try: 
        subnet_id = client.describe_subnets(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [
                        data[instance]["Subnet"],
                    ]
                },
            ],
        )["Subnets"][0]["SubnetId"]
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print "...Failed"
        continue

    try:    
        response = client.run_instances(
            MaxCount=1,
            MinCount=1,
            BlockDeviceMappings=block_device_mappings,
            ImageId=base_ami_id,
            InstanceType=data[instance]["Type"],
            KeyName=base_key_pair_name,
            Monitoring={
                'Enabled': False
            },
            UserData='',
            DisableApiTermination=False,
            EbsOptimized=False,
            IamInstanceProfile={},
            InstanceInitiatedShutdownBehavior='stop',
            NetworkInterfaces=[
                {
                    'AssociatePublicIpAddress': False,
                    'DeleteOnTermination': True,
                    'Description': '',
                    'DeviceIndex': 0,
                    'Groups': [
                        sg1_id,
                        sg2_id,
                    ],
                    'PrivateIpAddress': data[instance]["IP"],
                    'SubnetId': subnet_id,
                },
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': instance_tags,
                },
            ]
        )
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print "...Failed..."
        continue
    print "...Success"
