APPNAME   = postos_anp_crawler
VERSION   = 0.5
PROJECT   = postos-anp

publish:
	@sudo docker build \
        -t ${APPNAME}:${VERSION} . && \
	docker tag ${APPNAME}:${VERSION} gcr.io/${PROJECT}/${APPNAME}:${VERSION} && \
	docker push gcr.io/${PROJECT}/${APPNAME}:${VERSION}


git-tag:
	@git tag v$(VERSION) && git push origin v$(VERSION)