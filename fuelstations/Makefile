APPNAME   = postos_anp_crawler
VERSION   = 0.5.3
PROJECT   = postos-anp

publish:
	@sudo docker build \
        -t ${APPNAME}:${VERSION} . && \
	docker tag ${APPNAME}:${VERSION} gcr.io/${PROJECT}/${APPNAME}:${VERSION} && \
	docker push gcr.io/${PROJECT}/${APPNAME}:${VERSION}


git-release:
	git add .
	git commit -m "v$(VERSION)"
	git tag v$(VERSION)
	git push
	git push --tags