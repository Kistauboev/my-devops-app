terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_droplet" "devops_server" {
  image  = "ubuntu-22-04-x64"
  name   = "devops-app-server"
  region = "nyc3"
  size   = "s-1vcpu-1gb"
  ssh_keys = ["devops-project"]  # ← This is the fixed line
}

output "server_ip" {
  value = digitalocean_droplet.devops_server.ipv4_address
}