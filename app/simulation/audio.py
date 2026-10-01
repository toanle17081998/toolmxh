import math
import asyncio
import wave
from pathlib import Path
import numpy as np


class SimulationAudioManager:
    async def generate_async(self, scenario, output_path):
        writer = asyncio.create_task(asyncio.to_thread(self.generate,scenario,output_path))
        try:
            return await asyncio.shield(writer)
        except asyncio.CancelledError:
            # A cancelled asyncio task cannot stop a thread. Keep project ownership
            # until the WAV writer closes, preventing immediate resume from racing it.
            await writer
            raise

    def generate(self, scenario, output_path):
        """Original, synchronized audio in one-second chunks, even for long videos."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rate = 44100
        rng = np.random.default_rng(scenario.seed)
        with wave.open(str(output_path), 'wb') as wav:
            wav.setparams((1,2,rate,0,'NONE','not compressed'))
            for second in range(scenario.duration):
                t = second + np.arange(rate)/rate
                samples = np.zeros(rate)
                if scenario.audio['music']:
                    for frequency in (130.81,164.81,196.0):
                        samples += .025*np.sin(math.tau*frequency*t)*(.8+.2*np.sin(math.tau*.25*t))
                if scenario.audio['engine_sound']:
                    samples += .025*np.sin(math.tau*65*t)*(1+.15*np.sin(math.tau*4*t))
                    samples += .008*rng.standard_normal(rate)
                if scenario.audio['sound_effects']:
                    for event in scenario.events:
                        if second-1 <= event['time'] <= second+1:
                            dt = t-event['time']
                            mask = (dt>=0)&(dt<.6)
                            elapsed = np.maximum(0,dt)
                            if event['type']=='success':
                                effect = .18*np.sin(math.tau*(523+220*elapsed)*elapsed)*np.exp(-elapsed*5)
                            elif event['type']=='landing':
                                effect = .25*np.sin(math.tau*90*elapsed)*np.exp(-elapsed*18)+.08*rng.standard_normal(rate)*np.exp(-elapsed*22)
                            else:
                                effect = .07*np.sin(math.tau*220*elapsed)*np.exp(-elapsed*12)
                            samples += effect*mask
                fade = np.minimum(1,np.maximum(0,(scenario.duration-t)/.25))
                wav.writeframes((np.clip(samples*fade,-.9,.9)*32767).astype('<i2').tobytes())
        return output_path
