terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# Configure the DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}

# Create a droplet
resource "digitalocean_droplet" "devops_server" {
  image  = "ubuntu-22-04-x64"
  name   = "devops-app-server"
  region = "nyc3"
  size   = "s-1vcpu-1gb"
  ssh_keys = [var.ssh_key_id]
}

# Output the server IP address
output "server_ip" {
  value = digitalocean_droplet.devops_server.ipv4_address
}