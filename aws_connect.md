# Connecting to the AWS EC2 Instance

This guide explains how to connect to the project's remote AWS EC2 instance using the provided private key file.

---

## 📌 Instance Details (from AWS Console)

* **Instance ID:** `i-056f98048f1836754`
* **Public IPv4:** `3.92.223.153`
* **Public DNS:** `ec2-3-92-223-153.compute-1.amazonaws.com`
* **Private Key File:** `quantum.pem` (located in the root of this project folder)
* **Instance Type:** `m7i-flex.large`
* **Region:** `us-east-1` (US East - N. Virginia)

---

## 🚀 Step-by-Step Connection Guide

### 1. Open Your Terminal
Navigate to the project root directory where the `quantum.pem` key is located:
```bash
cd <Path to Quantum Computing/quantum.pem>
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
  ssh -i "quantum.pem" ubuntu@3.92.223.153
  ```

* **For Amazon Linux / Red Hat / CentOS instances:**
  ```bash
  ssh -i "quantum.pem" ec2-user@3.92.223.153
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
