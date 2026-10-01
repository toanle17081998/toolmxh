"""Opt-in browser integration against a running dashboard."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    url = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:7861'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1366,'height':900})
        errors = []
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(url,wait_until='networkidle')
        # The existing dashboard uses Tailwind CDN; use DOM classes if the CDN is unavailable.
        page.select_option('#videoTypeSelect','simulation_video')
        assert page.locator('#shortTopicSettings').evaluate("e=>e.classList.contains('hidden')")
        assert page.locator('#shortModelSettings').evaluate("e=>e.classList.contains('hidden')")
        assert not page.locator('#simulationSettings').evaluate("e=>e.classList.contains('hidden')")
        assert page.input_value('#platformSelect')=='youtube'
        assert page.input_value('#simulationAspect')=='16:9'
        page.select_option('#platformSelect','tiktok')
        assert page.input_value('#simulationAspect')=='9:16'
        page.select_option('#durationSelect','custom')
        page.fill('#customDuration','90')
        page.fill('#simulationSeed','42')
        requests = []
        def capture(route):
            requests.append(route.request.post_data_json)
            route.fulfill(status=200,json={'project_id':'browser_sim','status':'STARTED'})
        page.route('**/api/generate',capture)
        page.route('**/api/progress/browser_sim',lambda route:route.fulfill(status=200,json={
            'stage':'SIMULATION_RENDERING','progress_percentage':25,'progress_message':'Rendering 1/3',
            'is_running':True,'task_info':{'status':'FAILED','error':'stale web attempt'},
            'config':{'video_type':'simulation_video'},'segments_progress':{'1':{'segment_id':1,'status':'RENDERING','duration':30}}}))
        page.click('#generateBtn')
        page.wait_for_function("document.getElementById('currentStatusText').textContent==='Rendering 1/3'")
        assert requests[0]['video_type']=='simulation_video'
        assert requests[0]['duration']==90
        assert requests[0]['seed']==42
        page.select_option('#videoTypeSelect','short_content')
        assert not page.locator('#shortModelSettings').evaluate("e=>e.classList.contains('hidden')")
        assert page.input_value('#durationSelect')=='60'
        assert page.input_value('#platformSelect')=='tiktok'
        page.route('**/api/progress/restart_sim',lambda route:route.fulfill(status=200,json={
            'stage':'SIMULATION_RENDERING','is_running':False,'progress_percentage':25,
            'config':{'video_type':'simulation_video'},'segments_progress':{}}))
        page.evaluate("selectProject('restart_sim')")
        page.wait_for_function("!document.getElementById('resumeSimulationBtn').classList.contains('hidden')")
        assert not errors, errors
        Path('outputs').mkdir(exist_ok=True)
        page.screenshot(path='outputs/dashboard-smoke.png',full_page=True)
        browser.close()
        print('Dashboard mode switching, payload, progress and short restoration passed')


if __name__=='__main__':
    main()
