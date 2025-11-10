terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "2.26.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_droplet" "devops_server" {
  image  = "ubuntu-22-04-x64"
  name   = "devops-app-server"
  region = "nyc1"
  size   = "s-1vcpu-1gb"
  ssh_keys = [var.ssh_key_id]
}

output "server_ip" {
  value = digitalocean_droplet.devops_server.ipv4_address
}