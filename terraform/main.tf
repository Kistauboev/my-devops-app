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

data "digitalocean_ssh_key" "devops_key" {
  name = "devops-project"
}

resource "digitalocean_droplet" "devops_server" {
  image  = "ubuntu-22-04-x64"
  name   = "devops-app-server"
  region = "nyc1"
  size   = "s-1vcpu-512mb-10gb"
  ssh_keys = [data.digitalocean_ssh_key.devops_key.id]
}

output "server_ip" {
  value = digitalocean_droplet.devops_server.ipv4_address
}