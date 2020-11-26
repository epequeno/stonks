# build statically linked binary for use with scratch image
FROM rust:1-slim as builder
WORKDIR /usr/src/app
RUN apt-get update && apt-get install musl-tools -y
RUN rustup override set nightly
RUN rustup target add x86_64-unknown-linux-musl
COPY . .
RUN cargo install --target x86_64-unknown-linux-musl --path .

# build final image
FROM scratch
COPY --from=builder /usr/local/cargo/bin/stonks .
USER 1000
EXPOSE 8000
CMD [ "./stonks" ]
