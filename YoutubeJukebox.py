import json
from pathlib import Path

import os
import re
import requests
import youtube_dl
from requests import RequestException

from core.base.model.AliceSkill import AliceSkill
from core.base.model.Intent import Intent
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import AnyExcept, IntentHandler, Online


class YoutubeJukebox(AliceSkill):
	"""
	Author: Jierka
	Description: Allows to play music from youtube
	"""

	_INTENT_SEARCH_MUSIC = Intent('SearchMusic')

	def getWildcard(self, session):
		if isinstance(session.payload, str):
			inputt = json.loads(session.payload)['input']
		else:
			inputt = session.payload['input']

		utterances = self.getUtterancesByIntent(self._INTENT_SEARCH_MUSIC)
		self.logDebug(f'Raw input {inputt}')

		inputtList = inputt.split()
		for utterance in utterances:
			inputtList = [value for value in inputtList if value not in utterance.split()]

		clearInput = ' '.join(inputtList)

		self.logDebug(f'Cleaned input {clearInput}')

		return clearInput


	@IntentHandler(_INTENT_SEARCH_MUSIC)
	@AnyExcept(exceptions=RequestException, text='noServer', printStack=True)
	@Online
	def searchMusicIntent(self, session: DialogSession):
		wildcardQuery = self.getWildcard(session)

		self.endSession(sessionId=session.sessionId)

		response = requests.get('https://www.youtube.com/results', {'search_query':wildcardQuery})
		response.raise_for_status()
		videolist = re.findall(r'href=\"/watch\?v=(.{11})', response.text)

		if not videolist:
			self.say(text=self.randomTalk(text='noMatch', replace=[wildcardQuery]), siteId=session.siteId)
			return

		videoKey = videolist[0]
		videoUrl = f'https://www.youtube.com/watch?v={videoKey}'
		self.logInfo(f'Music video found {videoUrl}')

		youtubeDlOptions = {
			'outtmpl': '%(id)s.%(ext)s',
			'format': 'bestaudio/best',
			'postprocessors': [{
				'key': 'FFmpegExtractAudio',
				'preferredcodec': 'mp3',
				'preferredquality': '192',
			}]
		}

		resourceDir = self.getResource(resourcePathFile='audio')
		outputFile = Path(resourceDir, f'{videoKey}.mp3')

		if not os.path.isfile(outputFile):
			with youtube_dl.YoutubeDL(youtubeDlOptions) as ydl:
				os.chdir(str(resourceDir))
				ydl.download([videoUrl])

		self.Commons.runRootSystemCommand(['sudo', 'mpg123', outputFile])
