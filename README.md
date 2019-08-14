# selenium-mota

Play mota with selenium.

Python2.7 script though migration to py3 should be easy.

tested with docker `joyzoursky/python-chromedriver:2.7-alpine3.7-selenium`.

## run

```
git clone https://github.com/ThinerDAS/selenium-mota.git
wget https://h5mota.com/games/yinhe/yinhe.zip && unzip yinhe.zip
cd selenium-mota
docker run -v $(pwd):$(pwd) -w $(pwd) -it joyzoursky/python-chromedriver:2.7-alpine3.7-selenium python ./script.py ../yinhe
```