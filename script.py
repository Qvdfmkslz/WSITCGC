import asyncio
from pyppeteer import launch
from github import Github
import os

# Define directory_path at a higher scope
directory_path = os.environ.get('GITHUB_WORKSPACE', '/github/workspace')

async def scrape_data(url, file_number):
    browser = await launch({
        'headless': False,
    })
    page = await browser.newPage()

    # Set a real user agent
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Go to the URL and wait for the table to be present
    await page.goto(url, {'waitUntil': 'domcontentloaded'})
    await page.waitForSelector('#table_1')

    # Your evaluate script
    scraped_data = await page.evaluate('''() => {
        const table = document.getElementById('table_1');
        const rows = table.getElementsByTagName('tr');

        const data = [];

        for (let i = 1; i < rows.length; i++) {
            const columns = rows[i].getElementsByTagName('td');
            const rowData = {
                'Settings': columns[0].textContent.trim(),
                'Details': columns[1].textContent.trim(),
            };
            data.push(rowData);
        }

        return data;
    }''')

    await browser.close()

    # Save the result to a text file with a numbered prefix
    file_path = os.path.join(directory_path, f'Data_{file_number}.txt')
    with open(file_path, 'w') as file:
        for row in scraped_data:
            file.write(f"{row['Settings']}: {row['Details']}\n")
    print(f"Scraped data for {url} saved to '{file_path}'.")
    return file_path

async def main():
    urls = [
        'https://www.iptunnels.com/complete-guides-using-vmess-websocket/',
        'https://www.iptunnels.com/complete-guides-using-vless-websocket/',
        'https://www.iptunnels.com/how-to-use-the-linux-ping-command/',
        'https://www.iptunnels.com/how-to-install-linux-ubuntu/',
        'https://www.iptunnels.com/how-to-install-and-use-linux-screen/'
    ]

    file_paths = []
    for i, url in enumerate(urls, 1):
        file_paths.append(await scrape_data(url, i))

    all_configs = ["proxies:"]
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            data_block = file.read()

        values = {}
        for line in data_block.split('\n'):
            if ':' in line:
                key, value = map(str.strip, line.split(':', 1))
                values[key] = value

        type_suffix = '-ws' if values['Type'] == 'vmess-ws' or values['Type'] == 'vless-ws' else ''

        # Remove the '-ws' suffix from 'vmess' and 'vless'
        type_suffix = type_suffix.rstrip('-ws')

        clash_config = f"""\
  - name: {values['Current Usage']} - {values['Last Modified Auth']}
    type: {'vmess' if values['Type'] == 'vmess-ws' else 'vless'}{type_suffix}
    server: {values['Domain']}
    port: {values['Port HTTP'].split(',')[0]}  # Use the first port from the list
    uuid: {values['Password/UUID']}
    alterId: 0
    cipher: auto
    network: ws
    tls: false
    ws-opts:
      path: {values['Path']}   
      headers:
        Host: Open.spotify.com
    udp: true  # Add UDP support
"""

        all_configs.append(clash_config)

        os.remove(file_path)
        print(f"Deleted: {file_path}")

    resulting_txt = '\n'.join(all_configs)

    output_file_path = os.path.join(directory_path, 'Raws.txt')
    with open(output_file_path, 'w') as output_file:
        output_file.write(resulting_txt)

    print(f"Configs saved to: {output_file_path}")

    # GitHub upload
    github_username = 'Qvdfmkslz'
    github_repository = 'WSITCGC'
    github_token = os.environ.get('GITHUB_TOKEN')

    # Create a GitHub instance
    g = Github(github_token)

    # Get the specified repository
    repo = g.get_user().get_repo(github_repository)

    # Read the content of the local Raws.txt file
    with open(output_file_path, 'r') as file:
        content = file.read()

    remote_raws_file_path = 'Raws.txt'

    try:
        # Try to get the file if it already exists
        existing_file = repo.get_contents(remote_raws_file_path)
        repo.update_file(remote_raws_file_path, "Upload Raws.txt", content, existing_file.sha)
        print(f"File '{remote_raws_file_path}' updated on GitHub.")
    except Exception as e:
        # If the file does not exist, create a new one
        print(f"Exception: {e}")
        repo.create_file(remote_raws_file_path, "Upload Raws.txt", content)
        print(f"File '{remote_raws_file_path}' created on GitHub.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred: {e}")
