# Connecting to the AWS EC2 Instance

This guide explains how to connect to the project's remote AWS EC2 instance using the provided private key file.

---

## 📌 Instance Details (from AWS Console)

* **Instance ID:** `i-0aa88607ce0e5f4c9`
* **Public IPv4:** `18.61.219.164`
* **Public DNS:** `ec2-18-61-219-164.ap-south-2.compute.amazonaws.com`
* **Private Key File:** `quantum.pem` (located in the root of this project folder)
* **Instance Type:** `t3.small`
* **Region:** `ap-south-2` (Asia Pacific - Hyderabad)

---

## 🚀 Step-by-Step Connection Guide

### 1. Open Your Terminal
Navigate to the project root directory where the `quantum.pem` key is located:
```bash
cd "/Users/hari/Documents/Quantum Computing"
```

### 2. Set Secure Permissions on the Private Key
SSH will reject the key if its permissions are too open. Run the following command to make the key readable only by you:
```bash
chmod 400 quantum.pem
```

### 3. Connect via SSH
Run the SSH command to connect to the instance. Depending on the operating system of your instance, the username may vary:

* **For Ubuntu / Debian instances (Recommended / Default):**
  ```bash
  ssh -i "quantum.pem" ubuntu@18.61.219.164
  ```

* **For Amazon Linux / Red Hat / CentOS instances:**
  ```bash
  ssh -i "quantum.pem" ec2-user@18.61.219.164
  ```

---

## 🛠️ Troubleshooting

### ⚠️ Permission Denied (publickey)
If you get a public key permission error, ensure:
1. You are running the command from the directory containing `quantum.pem`.
2. You have set permissions correctly with `chmod 400 quantum.pem`.
3. You are using the correct username (`ubuntu` or `ec2-user`).

### ⏳ Connection Timeout
If the connection hangs or times out:
1. Verify the instance state is **Running** in the AWS console.
2. Confirm the Public IPv4 address hasn't changed (if the instance was stopped and restarted, a new dynamic IP may have been assigned).
3. Ensure that the Security Group for the instance allows inbound SSH traffic (port 22) from your current public IP address.
