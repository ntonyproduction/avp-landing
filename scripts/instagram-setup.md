# Instagram publishing — one-time setup

`scripts/avp_instagram.py` posts photos and carousels to @audiovisionproductions without a
browser. This is the setup you only do once. Everything here happens in *your* accounts, so
run these steps yourself — the script never asks for a password and never sees one.

## What you end up with

A Facebook **Page access token that has no expiry date**, stored in `~/.avp/instagram/credentials.json`
alongside the YouTube one. No 60-day refresh, no re-auth, unless you change your Facebook
password or remove the app.

## Before you start

The Instagram account must be a **Business or Creator** account and **linked to a Facebook Page**.
Yours already is — that is what ManyChat is connected through — so there is nothing to change.

## 1. Create the Meta app

1. Go to <https://developers.facebook.com/apps/> and click **Create app**
2. Give it a name only you see, e.g. `AVP Publishing`
3. When it asks for a use case, pick **Other**, then app type **Business**
4. Create it, then from the app dashboard add the **Instagram** product

Leave the app in **Development** mode. You are the admin, you are posting to your own account,
so it works as-is. This is the step people think needs App Review — it does not.

## 2. Copy the app credentials

App dashboard → **App settings → Basic**. Copy the **App ID** and **App Secret** (you have to
click Show). Keep them in front of you for step 4.

## 3. Generate a short-lived token

1. Go to the **Graph API Explorer**: <https://developers.facebook.com/tools/explorer/>
2. Top right, set **Meta App** to the app you just made
3. Set the token type to **User token**
4. Under **Permissions**, add all of these:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
5. Click **Generate Access Token**, log in, and when it asks which Pages and which Instagram
   account to allow, **tick the audiovisionproductions Page and Instagram account**
6. Copy the token out of the box

That token dies in about an hour, so go straight to step 4. It only has to live long enough to
be traded for the permanent one.

## 4. Trade it for the permanent token

```
py -3 -u scripts/avp_instagram.py auth --app-id YOUR_APP_ID --app-secret YOUR_APP_SECRET --token PASTED_TOKEN
```

It trades the short-lived token for a long-lived one, finds the Page linked to
@audiovisionproductions, takes that Page's token, and writes the store. It prints every Page it
skips, so if it cannot find the right one you can see why.

Check it landed:

```
py -3 -u scripts/avp_instagram.py whoami
```

That prints the account it will post as, whether the token expires, and how much of the
100-posts-per-24h quota is used.

## Posting

```
py -3 -u scripts/avp_instagram.py post --folder "C:\Users\Client\Desktop\Chatterbox - Ads\Carousel" --caption-file "C:\Users\Client\Desktop\Chatterbox - Ads\Carousel\caption.txt" --dry-run
```

`--dry-run` prints the images in the order they will appear and the exact caption, and touches
nothing. Drop it to actually post. Add `--stop-before-publish` to build the post and leave the
final publish as a separate command.

Two things worth knowing:

- **Filename order is post order.** Fine for `slide-1` … `slide-6`; if you ever have ten slides,
  `slide-10` sorts before `slide-2`, so name them `01`…`10` or pass the paths explicitly.
- **The images get committed to this repo** under `art/ig/<slug>/` and pushed, because Instagram
  fetches them from a public URL rather than taking an upload. They are ads you are publishing
  anyway, but that is where they live afterwards.

## Captions

Always use `--caption-file`, not `--caption`. Emoji and `#` survive a UTF-8 file; they do not
reliably survive a Windows command line.
