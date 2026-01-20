export const prerender = false;

export async function GET() {
    const apiUrl =
        "https://api.github.com/repos/a4ye/personal-website-v2/commits?per_page=1";
    const token = import.meta.env.GITHUB_TOKEN;

    const response = await fetch(apiUrl, {
        headers: {
            Accept: "application/vnd.github.v3+json",
            ...(token && { Authorization: `Bearer ${token}` }),
        },
    });

    if (!response.ok) {
        return new Response(JSON.stringify({ error: "Failed to fetch commit data" }), {
            status: response.status,
            headers: { "Content-Type": "application/json" },
        });
    }

    const data = await response.json();
    const shortSha = data[0].sha.substring(0, 7);
    const commitUrl = data[0].html_url;
    const commitDate = data[0].commit.author.date;

    return new Response(JSON.stringify({ shortSha, commitUrl, commitDate }), {
        headers: { "Content-Type": "application/json" },
    });
}
