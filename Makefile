.PHONY: test tools lab validate clean

test:
	python3 -m unittest discover -s tests -v

clean:
	python3 -m balboa clean --apply

tools:
	python3 -m balboa tools

lab:
	python3 -m balboa render --flavor server --lab --output build/server
	python3 -m balboa render --flavor workstation --lab --output build/workstation
	python3 -m balboa render --flavor laptop --lab --output build/laptop

validate:
	python3 -m balboa validate build/server/installation.ks --packages
	python3 -m balboa validate build/workstation/installation.ks --packages
	python3 -m balboa validate build/laptop/installation.ks --packages
