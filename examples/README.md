# Example Context Files

These are **sanitized example files** showing how to structure your context for different use cases.

⚠️ **All values in these examples are placeholders!** Your actual context file will contain:
- Real IP addresses
- Real hostnames
- Real SSH key names
- Real project details

## Files

### `homelab_context.json`
Example for a home lab setup with:
- Multiple servers (NAS, Proxmox, Pi-hole)
- GPU workstation
- Internal network configuration
- Active infrastructure projects

### `developer_context.json`
Example for a software developer with:
- Development machine (MacBook)
- Remote servers (staging, production)
- Active coding projects
- Deployment workflows

## Using These Examples

1. **Don't copy directly** - use `setup.py` to generate your initial context
2. **Use as reference** - see how to structure servers, projects, and notes
3. **Adapt to your needs** - add/remove sections based on what you actually use

## Security Reminder

Your actual `~/claude_context.json` will contain sensitive data. Never commit it to version control!

