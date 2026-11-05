#!/usr/bin/env python3
"""Generate publisher text, original graphics and Play shortcut labels from one config."""
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from prepare_play_sources import MARK, WORDMARK, NAMES, png

ROOT=Path(__file__).resolve().parent.parent
brand=json.loads((ROOT/'release/brand.json').read_text())
support=brand['supportEmail'] or '[Support email must be added before publication]'
policy=f'''{brand['appName']} — Privacy policy
Prepared 5 November 2026
Publisher: {brand['publisherName']}
Website: {brand['website']}
Contact: {support}

Your documents
Documents, images, audio and other files you open are processed on your device. The app does not upload your documents to the publisher or an AI service. Android's document picker grants access only to files you select. If you choose a cloud-storage provider in that picker, that provider handles storage under its own terms.

Accounts, advertising and analytics
The app does not require an account. The publisher has not added advertising, analytics, tracking or payment SDKs. The bundled Mozilla browser runtime executes the editors locally. Its open-source notices and corresponding source are available in About & licenses.

Network access
The editors load their files from an on-device loopback server; this traffic stays on your device. Editor web requests to outside sites are blocked. The Google Play edition's update button uses Google's Play In-App Updates library; Google Play handles availability checks, downloads and installation under Google's terms and privacy practices. The separate Huawei edition checks the publisher's public GitHub releases and downloads a signed Mtouaa APK only when you choose to update. GitHub receives normal connection information, such as your IP address and the update client's user agent; document contents are not sent. Installing an update requires your confirmation and can close the app, so save your work first. Opening Support or the public privacy page uses your browser, where the website's privacy practices apply.

Local storage and deletion
Editor preferences, browser storage and temporary import/export files may be stored locally. Selected documents are read through Android's granted document access and copied into private cache while the editor needs them. These import copies are removed when the editor closes or on the next app launch; originals are not changed. Temporary export files are cleared after use or on the next app launch. You choose where exported documents are saved. Clear the app's storage or uninstall it to remove its internal data; exported files remain where you saved them and can be deleted using your file manager.

Permissions
Internet and network-state permissions are needed by the local browser/server connection, browser runtime and optional update checks/downloads. The Huawei edition also requests permission to open Android's APK installer; you choose whether to allow installations from it in Android settings and confirm each installation. That installer permission is absent from the Google Play edition. The app does not request broad storage access, contacts, location, microphone or camera permissions. Android's file picker handles document access.

Children
This general-purpose creative suite is not specifically designed for children. The Play Console target-audience declaration must match the intended audience selected by the publisher.

Changes and questions
This policy will be updated when the app's data practices change. Contact the publisher at the address above with privacy questions.
'''
shared=ROOT/'app/src/shared/assets';shared.mkdir(parents=True,exist_ok=True)
(shared/'privacy-policy.txt').write_text(policy)
# ensureBuiltIn retains an installed extension when its version is unchanged.
# Tie that version to Android's monotonically increasing versionCode so an app
# update also refreshes its packaged bridge, without a separate manual version.
version_code=int(re.search(r'\bversionCode\s+(\d+)',(ROOT/'app/build.gradle').read_text())[1])
bridge_manifest=shared/'gecko-extension/manifest.json'
bridge=json.loads(bridge_manifest.read_text())
bridge['version']=f'1.0.{version_code // 65536}.{version_code % 65536}'
bridge_manifest.write_text(json.dumps(bridge,indent=2)+'\n')
out=ROOT/'release/store';out.mkdir(parents=True,exist_ok=True)
(out/'privacy-policy.txt').write_text(policy)
import html
(out/'privacy-policy.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(brand['appName'])+' privacy policy</title><style>body{max-width:760px;margin:48px auto;padding:0 24px;font:17px/1.65 system-ui;color:#142838;white-space:pre-wrap}</style><body>'+html.escape(policy)+'</body></html>')
import create_store_graphic
(out/'mark.svg').write_text(MARK)
(out/'wordmark.svg').write_text(WORDMARK.replace('COLOR','#142838'))
(out/'short-description.txt').write_text('Create and edit documents, PDFs, images, slides and more—offline.\n')
(out/'full-description.txt').write_text(f'''{brand['appName']} brings 15 creative tools together in one app, with all editors included for offline use after installation.

Write documents, work with PDFs and spreadsheets, prepare slides, edit images and vectors, explore page layouts, and work with audio, video, motion, CAD and textures.

• Your files are processed on your device.
• No account required.
• Open and export files using Android's document picker.
• Add individual editor shortcuts to your home screen.
• Use full screen for more workspace on a tablet.

The editors use desktop-style interfaces. A larger screen and a keyboard are recommended. Features and supported formats vary between editors. Save and verify exports before switching tools; not every upstream desktop feature is available in the browser editions.

Published independently by {brand['publisherName']}. Based on open-source editing engines, with original authors and licences credited inside the app. This edition is not affiliated with the upstream maintainers or Mozilla.
''')
res=ROOT/'app/src/play/res';(res/'drawable-nodpi').mkdir(parents=True,exist_ok=True)
catalog=json.loads((ROOT/'tools/suite-lock.json').read_text())
manifest=ROOT/'app/src/play/AndroidManifest.xml';tree=ET.parse(manifest);ns='http://schemas.android.com/apk/res/android';ET.register_namespace('android',ns);ET.register_namespace('tools','http://schemas.android.com/tools')
application=tree.getroot().find('application')
for alias in list(application.findall('activity-alias')):application.remove(alias)
for app in catalog:
    alias=''.join(c for c in app['name'] if c.isalnum())
    ET.SubElement(application,'activity-alias',{f'{{{ns}}}name':'.'+alias,f'{{{ns}}}label':NAMES[app['id']],
        '{http://schemas.android.com/tools}replace':'android:label'})
    (res/'drawable-nodpi'/('ic_'+app['id'].replace('-','_')+'.png')).write_bytes(png(128))
ET.indent(tree,space='    ') if hasattr(ET,'indent') else None
tree.write(manifest,encoding='unicode',xml_declaration=True)
import copy
huawei=copy.deepcopy(tree)
huawei.getroot().insert(0,ET.Element('uses-permission',{f'{{{ns}}}name':'android.permission.REQUEST_INSTALL_PACKAGES'}))
provider=ET.SubElement(huawei.getroot().find('application'),'provider',{
    f'{{{ns}}}name':'androidx.core.content.FileProvider',f'{{{ns}}}authorities':'${applicationId}.updates',
    f'{{{ns}}}exported':'false',f'{{{ns}}}grantUriPermissions':'true'})
ET.SubElement(provider,'meta-data',{f'{{{ns}}}name':'android.support.FILE_PROVIDER_PATHS',f'{{{ns}}}resource':'@xml/update_paths'})
huawei_manifest=ROOT/'app/src/huawei/AndroidManifest.xml';huawei_manifest.parent.mkdir(parents=True,exist_ok=True)
ET.indent(huawei,space='    ') if hasattr(ET,'indent') else None
huawei.write(huawei_manifest,encoding='unicode',xml_declaration=True)
extension=ROOT/'app/src/play/assets/gecko-extension';extension.mkdir(parents=True,exist_ok=True)
for script in ['network.js','content.js']:
    (extension/script).write_text((shared/'gecko-extension'/script).read_text().replace("'43871'","'43872'"))
preview=ROOT/'app/src/preview/assets/gecko-extension';preview.mkdir(parents=True,exist_ok=True)
for script in ['network.js','content.js']:
    (preview/script).write_text((shared/'gecko-extension'/script).read_text().replace("'43871'","'43873'"))
huawei_extension=ROOT/'app/src/huaweiRelease/assets/gecko-extension';huawei_extension.mkdir(parents=True,exist_ok=True)
for script in ['network.js','content.js']:
    (huawei_extension/script).write_text((shared/'gecko-extension'/script).read_text().replace("'43871'","'43874'"))
notices=ROOT/'app/src/play/assets/THIRD_PARTY_NOTICES.txt'
notices.write_text(re.sub(r'^Publisher: .*$',
    lambda _: f"Publisher: {brand['publisherName']}. Website: {brand['website']}",
    notices.read_text(),flags=re.M))
print('Prepared Mtouaa branding, privacy draft, store text, original icons and shortcut labels.')
if not brand['supportEmail']:print('Submission remains gated: support email is not configured.')
