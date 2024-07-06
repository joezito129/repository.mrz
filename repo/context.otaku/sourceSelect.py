import sys
import xbmc

if __name__ == '__main__':
    item = sys.listitem
    path = item.getPath()
    resume_time = item.getVideoInfoTag().getResumeTime()

    path += '?source_select=true'
    if resume_time > 0:
        path += f'&resume={resume_time}'
    xbmc.executebuiltin('PlayMedia(%s)' % path)
