#!/bin/bash

BLUE="\e[34m"
NC="\e[0m"

# Blow away the docker universe. Useful when sanity checking.
printf "${BLUE}Stopping all docker containers...${NC}\n"
containers=$(docker ps -q)
if [[ ! -z $containers ]]; then
  docker kill $containers;
fi

printf "${BLUE}Deleting all docker images...${NC}\n"
docker rmi -f $(docker image ls -q) 2> /dev/null

printf "${BLUE}Deleting all docker volumes...${NC}\n"
docker volume rm $(docker volume ls -q) 2> /dev/null

printf "${BLUE}Deleting all docker cached build assets + other random cruft...${NC}\n"
docker system prune -f 2> /dev/null
